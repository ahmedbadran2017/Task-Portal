"""AI assist — rewrite ticket descriptions in clean English.

Same integration pattern as the JoyAgent runtime (supplier_portal): raw
requests.post to the Anthropic Messages API, key from site_config
(`anthropic_api_key`), deterministic retry on transient errors. No SDK
dependency so nothing new is installed on the bench.
"""
import time

import frappe
import requests
from frappe import _

from task_hub.api.utils import gate_read

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
RETRY_STATUSES = {429, 500, 502, 503, 529}
ATTEMPTS = 3
MAX_INPUT_CHARS = 5000

SYSTEM_PROMPT = (
    "You rewrite internal task/ticket descriptions for an e-commerce company. "
    "The input may be in any language (often Arabic, Turkish, or mixed). "
    "Rewrite it as clear, professional English.\n\n"
    "Rules:\n"
    "- Preserve every fact: numbers, order/invoice IDs, product names, dates, "
    "URLs, and names stay exactly as written.\n"
    "- Do not add information, assumptions, or pleasantries.\n"
    "- Keep it concise; use short lines or bullet points when the input lists "
    "several things.\n"
    "- If part of the text is already good English, keep it.\n"
    "- Output ONLY the rewritten description — no preamble, no quotes, no "
    "explanations."
)


def _api_key():
    return (frappe.conf.get("anthropic_api_key") or "").strip()


def _model():
    # Same site_config layering as the JoyAgent: secrets + infra knobs live in
    # site_config.json, feature toggles in Task Hub Settings.
    return (frappe.conf.get("task_hub_ai_model") or "claude-opus-5").strip()


def is_enabled():
    """Key configured AND the settings toggle is on."""
    if not _api_key():
        return False
    try:
        return bool(frappe.get_cached_doc("Task Hub Settings").get("ai_polish", 1))
    except Exception:
        return False


def call_anthropic(system, user_content, max_tokens=1500):
    """Shared Messages-API call: retry on transient errors, raise a clean
    frappe error otherwise, return the response text."""
    body = {
        "model": _model(),
        "max_tokens": max_tokens,
        # Short assist tasks — low effort keeps them fast and cheap.
        "output_config": {"effort": "low"},
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
    }
    headers = {
        "x-api-key": _api_key(),
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    last_error = None
    for i in range(ATTEMPTS):
        try:
            resp = requests.post(ANTHROPIC_URL, headers=headers, json=body, timeout=60)
            if resp.status_code in RETRY_STATUSES:
                last_error = f"HTTP {resp.status_code}"
                time.sleep(1.5 * (i + 1))
                continue
            if resp.status_code >= 400:
                frappe.log_error(title=f"Task Hub AI {resp.status_code}",
                                 message=(resp.text or "")[:2000])
                frappe.throw(_("AI assist failed — please try again."))
            data = resp.json()
            if data.get("stop_reason") == "refusal":
                frappe.throw(_("AI assist is not available for this text."))
            text = "".join(
                b.get("text", "") for b in data.get("content", [])
                if b.get("type") == "text"
            ).strip()
            if not text:
                frappe.throw(_("AI assist returned nothing — please try again."))
            return text
        except requests.RequestException as e:
            last_error = str(e)
            time.sleep(1.5 * (i + 1))

    frappe.log_error(title="Task Hub AI unreachable", message=str(last_error)[:2000])
    frappe.throw(_("AI assist is temporarily unavailable — please try again."))


@frappe.whitelist()
def polish_description(text):
    """Rewrite `text` (any language) as clean professional English."""
    gate_read()
    if not is_enabled():
        frappe.throw(_("AI assist is not available."))

    text = (text or "").strip()
    if not text:
        frappe.throw(_("Nothing to rewrite — the description is empty."))
    if len(text) > MAX_INPUT_CHARS:
        frappe.throw(_("The description is too long for AI rewrite ({0} character limit).")
                     .format(MAX_INPUT_CHARS))
    return {"polished": call_anthropic(SYSTEM_PROMPT, text)}


TRIAGE_SYSTEM = (
    "You triage internal tickets for Justyol, an e-commerce company. Given a "
    "ticket (any language) and the list of team workspaces, decide:\n"
    "- priority: Urgent (business stopped / money leaking now), High (blocks "
    "someone's work today), Medium (normal), Low (nice to have)\n"
    "- ticket_type: Problem (something broken), Request (asking for work), "
    "Task (planned work)\n"
    "- workspace: the team that should own it, from the provided list only\n\n"
    "Respond with ONLY a JSON object, no prose, no code fences:\n"
    '{"priority": "...", "ticket_type": "...", "workspace": "...", '
    '"reason": "<one short sentence in the ticket\'s language>"}'
)


@frappe.whitelist()
def triage(title, description=""):
    """Suggest priority / type / owning workspace for a draft ticket."""
    gate_read()
    if not is_enabled():
        frappe.throw(_("AI assist is not available."))
    title = (title or "").strip()
    if not title:
        frappe.throw(_("Write a title first."))

    workspaces = frappe.get_all(
        "Hub Workspace", fields=["name", "department"], order_by="name")
    ws_lines = "\n".join(
        f"- {w.name}" + (f" (department: {w.department})" if w.department else "")
        for w in workspaces)
    user_content = (
        f"Workspaces:\n{ws_lines}\n\n"
        f"Ticket title: {title}\n"
        f"Description:\n{(description or '')[:3000]}"
    )
    raw = call_anthropic(TRIAGE_SYSTEM, user_content, max_tokens=300)

    import json as _json
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        out = _json.loads(raw)
    except Exception:
        frappe.throw(_("AI triage returned an unexpected answer — try again."))

    valid_ws = {w.name for w in workspaces}
    return {
        "priority": out.get("priority") if out.get("priority") in
            ("Urgent", "High", "Medium", "Low") else None,
        "ticket_type": out.get("ticket_type") if out.get("ticket_type") in
            ("Task", "Problem", "Request") else None,
        "workspace": out.get("workspace") if out.get("workspace") in valid_ws else None,
        "reason": (out.get("reason") or "")[:300],
    }


ASK_SYSTEM = (
    "You are the Justyol Task Hub assistant. Answer the user's question using "
    "ONLY the ticket data provided — never invent tickets or numbers. Mention "
    "ticket IDs (TKT-…) when referring to specific tickets. Answer in the "
    "same language as the question, concisely. If the data can't answer the "
    "question, say so plainly."
)


def _ask_context(question):
    """Visibility-scoped snapshot of the caller's hub, compact enough to be
    cheap and rich enough to answer real questions."""
    from task_hub.api.utils import visibility_sql
    vis, params = visibility_sql()

    def rows(sql, extra=None):
        return frappe.db.sql(sql, dict(params, **(extra or {})), as_dict=True)

    lines = []
    counts = rows(f"""SELECT status, COUNT(*) n FROM `tabHub Ticket`
                      WHERE 1=1{vis} GROUP BY status""")
    lines.append("Counts by status: " +
                 ", ".join(f"{r.status}={r.n}" for r in counts))
    by_ws = rows(f"""SELECT workspace, COUNT(*) n FROM `tabHub Ticket`
                     WHERE status IN ('Open','In Progress','In Review'){vis}
                     GROUP BY workspace""")
    lines.append("Open by workspace: " +
                 ", ".join(f"{r.workspace}={r.n}" for r in by_ws if r.workspace))

    def fmt(r):
        parts = [r.name, r.title[:70], r.status, r.priority]
        if r.assigned_to:
            parts.append("assignee:" + r.assigned_to.split("@")[0])
        if r.get("due_date"):
            parts.append(f"due:{r.due_date}")
        if r.get("workspace"):
            parts.append(f"ws:{r.workspace}")
        return " | ".join(str(p) for p in parts)

    base = ("SELECT name, title, status, priority, assigned_to, due_date, "
            "workspace FROM `tabHub Ticket` WHERE 1=1")
    breached = rows(f"""{base}{vis} AND sla_breached = 1
                        AND status IN ('Open','In Progress','In Review')
                        ORDER BY modified DESC LIMIT 10""")
    if breached:
        lines.append("SLA-breached open tickets:")
        lines += ["  " + fmt(r) for r in breached]
    due_soon = rows(f"""{base}{vis} AND due_date IS NOT NULL
                        AND due_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                        AND status IN ('Open','In Progress','In Review')
                        ORDER BY due_date LIMIT 10""")
    if due_soon:
        lines.append("Due within 7 days:")
        lines += ["  " + fmt(r) for r in due_soon]
    recent = rows(f"{base}{vis} ORDER BY modified DESC LIMIT 10")
    if recent:
        lines.append("Recently updated:")
        lines += ["  " + fmt(r) for r in recent]

    # Keyword matches from the question itself.
    words = [w for w in (question or "").split() if len(w) >= 3][:4]
    if words:
        conds = " OR ".join(f"title LIKE %(w{i})s" for i in range(len(words)))
        extra = {f"w{i}": f"%{w}%" for i, w in enumerate(words)}
        matches = rows(f"{base}{vis} AND ({conds}) ORDER BY modified DESC LIMIT 8",
                       extra)
        if matches:
            lines.append("Tickets matching the question keywords:")
            lines += ["  " + fmt(r) for r in matches]
    return "\n".join(lines)[:8000]


@frappe.whitelist()
def ask(question):
    """Natural-language Q&A over the caller's visible tickets."""
    gate_read()
    if not is_enabled():
        frappe.throw(_("AI assist is not available."))
    question = (question or "").strip()
    if not question:
        frappe.throw(_("Ask something first."))
    if len(question) > 500:
        frappe.throw(_("Keep the question under 500 characters."))

    context = _ask_context(question)
    user_content = f"Ticket data:\n{context}\n\nQuestion: {question}"
    return {"answer": call_anthropic(ASK_SYSTEM, user_content, max_tokens=800)}
