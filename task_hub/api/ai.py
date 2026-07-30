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

    body = {
        "model": _model(),
        "max_tokens": 1500,
        # Simple rewrite task — low effort keeps it fast and cheap.
        "output_config": {"effort": "low"},
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": text}],
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
                frappe.throw(_("AI rewrite failed — please try again."))
            data = resp.json()
            if data.get("stop_reason") == "refusal":
                frappe.throw(_("AI rewrite is not available for this text."))
            polished = "".join(
                b.get("text", "") for b in data.get("content", [])
                if b.get("type") == "text"
            ).strip()
            if not polished:
                frappe.throw(_("AI rewrite returned nothing — please try again."))
            return {"polished": polished}
        except requests.RequestException as e:
            last_error = str(e)
            time.sleep(1.5 * (i + 1))

    frappe.log_error(title="Task Hub AI unreachable", message=str(last_error)[:2000])
    frappe.throw(_("AI rewrite is temporarily unavailable — please try again."))
