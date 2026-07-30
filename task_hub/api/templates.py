"""Task templates — one click turns a template into a ready ticket with its
checklist ("new campaign" = brief, design, copy, publish…)."""
import json

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from task_hub.api.utils import gate_read, gate_manager

FIELDS = ["name", "template_name", "workspace", "ticket_type", "priority",
          "due_in_days", "default_assignee", "title", "description"]


@frappe.whitelist()
def list_templates(workspace=None):
    gate_read()
    filters = {"workspace": workspace} if workspace else {}
    rows = frappe.get_all("Hub Task Template", filters=filters, fields=FIELDS,
                          order_by="template_name asc")
    for r in rows:
        r["checklist"] = [c.item for c in frappe.get_cached_doc(
            "Hub Task Template", r.name).checklist]
    return rows


@frappe.whitelist()
def save_template(**kwargs):
    """Create (no name) or update (with name); `checklist` is a JSON list of
    item strings."""
    gate_manager()
    name = kwargs.get("name")
    doc = (frappe.get_doc("Hub Task Template", name)
           if name else frappe.new_doc("Hub Task Template"))
    if not name and kwargs.get("template_name"):
        doc.template_name = kwargs["template_name"].strip()
    for f in ("workspace", "ticket_type", "priority", "default_assignee",
              "title", "description"):
        if f in kwargs and kwargs[f] is not None:
            doc.set(f, kwargs[f] or None)
    if "due_in_days" in kwargs and kwargs["due_in_days"] not in (None, ""):
        doc.due_in_days = max(0, min(365, int(kwargs["due_in_days"])))
    items = kwargs.get("checklist")
    if items is not None:
        if isinstance(items, str):
            items = json.loads(items)
        doc.checklist = []
        for it in items:
            it = (it or "").strip()
            if it:
                doc.append("checklist", {"item": it[:200], "done": 0})
    if not (doc.title or "").strip():
        frappe.throw(_("The template needs a ticket title."))
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def delete_template(name):
    gate_manager()
    frappe.delete_doc("Hub Task Template", name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": name}


@frappe.whitelist()
def create_from_template(template, title=None, due_date=None, assigned_to=None,
                         description=None):
    """Instantiate a template: ticket in the template's workspace with its
    checklist copied over. Explicit overrides win."""
    gate_read()
    tpl = frappe.get_doc("Hub Task Template", template)

    doc = frappe.new_doc("Hub Ticket")
    doc.title = (title or tpl.title or tpl.template_name)[:180]
    doc.description = description if description is not None else (tpl.description or "")
    doc.ticket_type = tpl.ticket_type or "Task"
    doc.priority = tpl.priority or "Medium"
    doc.workspace = tpl.workspace
    doc.assigned_to = assigned_to or tpl.default_assignee or None
    if doc.assigned_to and not frappe.db.exists("User", doc.assigned_to):
        doc.assigned_to = None
    if due_date:
        doc.due_date = due_date
    elif int(tpl.due_in_days or 0) > 0:
        doc.due_date = add_days(nowdate(), int(tpl.due_in_days))
    for c in tpl.checklist:
        doc.append("checklist", {"item": c.item, "done": 0})
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "title": doc.title, "workspace": doc.workspace}
