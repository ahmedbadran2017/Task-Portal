"""Request forms — Asana-style work intake between departments.

A manager designs a form (questions + defaults) per workspace; anyone in
the company fills it and a properly-routed ticket lands on that team's
board. No more "أطلب من القسم التاني إزاي؟".
"""
import json

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from task_hub.api.utils import gate_read, gate_manager, is_manager

FIELDS = ["name", "form_name", "workspace", "icon", "active", "help_text",
          "ticket_type", "priority", "default_assignee", "due_in_days"]


@frappe.whitelist()
def list_forms(all_forms=0):
    """Active forms for everyone; managers may ask for inactive ones too.

    The manager check is the point: without it `all_forms=1` handed any
    signed-in user the drafts and retired forms this promised to keep back.
    """
    gate_read()
    show_all = int(all_forms or 0) and is_manager()
    filters = {} if show_all else {"active": 1}
    rows = frappe.get_all("Hub Request Form", filters=filters, fields=FIELDS,
                          order_by="form_name asc")
    for r in rows:
        doc = frappe.get_cached_doc("Hub Request Form", r.name)
        r["questions"] = [
            {"question": q.question, "fieldtype": q.fieldtype,
             "required": q.required,
             "options": [o.strip() for o in (q.options or "").splitlines() if o.strip()]}
            for q in doc.questions
        ]
        r["workspace_icon"] = frappe.db.get_value("Hub Workspace", r.workspace, "icon") or ""
    return rows


@frappe.whitelist()
def save_form(**kwargs):
    """Create (no name) or update (with name); `questions` is a JSON list of
    {question, fieldtype, required, options}."""
    gate_manager()
    name = kwargs.get("name")
    doc = (frappe.get_doc("Hub Request Form", name)
           if name else frappe.new_doc("Hub Request Form"))
    if not name and kwargs.get("form_name"):
        doc.form_name = kwargs["form_name"].strip()
    for f in ("workspace", "icon", "help_text", "ticket_type", "priority",
              "default_assignee"):
        if f in kwargs and kwargs[f] is not None:
            doc.set(f, kwargs[f] or None)
    if "active" in kwargs:
        doc.active = 1 if kwargs["active"] in (1, "1", True, "true") else 0
    if "due_in_days" in kwargs and kwargs["due_in_days"] not in (None, ""):
        doc.due_in_days = max(0, min(365, int(kwargs["due_in_days"])))
    questions = kwargs.get("questions")
    if questions is not None:
        if isinstance(questions, str):
            questions = json.loads(questions)
        doc.questions = []
        for q in questions:
            label = (q.get("question") or "").strip()
            if not label:
                continue
            opts = q.get("options") or []
            if isinstance(opts, list):
                opts = "\n".join(opts)
            doc.append("questions", {
                "question": label[:200],
                "fieldtype": q.get("fieldtype") or "Text",
                "required": 1 if q.get("required") in (1, "1", True, "true") else 0,
                "options": opts,
            })
    if not doc.workspace:
        frappe.throw(_("The form needs a destination workspace."))
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def delete_form(name):
    gate_manager()
    frappe.delete_doc("Hub Request Form", name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": name}


@frappe.whitelist()
def submit_form(form, title, answers=None, due_date=None):
    """Turn a filled form into a routed ticket. `answers` is a JSON list of
    {question, answer} in form order."""
    gate_read()
    doc_form = frappe.get_doc("Hub Request Form", form)
    if not doc_form.active:
        frappe.throw(_("This form is no longer accepting requests."))
    title = (title or "").strip()
    if not title:
        frappe.throw(_("A short title is required."))

    if isinstance(answers, str):
        try:
            answers = json.loads(answers)
        except Exception:
            answers = []
    answers = answers or []

    # Required-question enforcement server-side (the UI validates too).
    answered = { (a.get("question") or "").strip(): (a.get("answer") or "").strip()
                 for a in answers }
    for q in doc_form.questions:
        if q.required and not answered.get(q.question, "").strip():
            frappe.throw(_("'{0}' is required.").format(q.question))

    lines = [f"Request via form: {doc_form.form_name}", ""]
    for a in answers:
        question = (a.get("question") or "").strip()
        answer = (a.get("answer") or "").strip()
        if not question or not answer:
            continue
        lines.append(f"• {question}")
        lines.append(f"  {answer[:2000]}")

    ticket = frappe.new_doc("Hub Ticket")
    ticket.title = f"{doc_form.form_name}: {title}"[:180]
    ticket.description = "\n".join(lines)
    ticket.ticket_type = doc_form.ticket_type or "Request"
    ticket.priority = doc_form.priority or "Medium"
    ticket.source_portal = "Other"
    ticket.workspace = doc_form.workspace
    assignee = doc_form.default_assignee
    if assignee and frappe.db.exists("User", assignee):
        ticket.assigned_to = assignee
    if due_date:
        ticket.due_date = due_date
    elif int(doc_form.due_in_days or 0) > 0:
        ticket.due_date = add_days(nowdate(), int(doc_form.due_in_days))
    ticket.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": ticket.name, "title": ticket.title, "workspace": ticket.workspace}
