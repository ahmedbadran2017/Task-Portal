"""
Hub Ticket CRUD + workflow API.

`create_ticket` is the ONE entrypoint every portal calls (from its Vue
frontend or server-side) to raise a task/problem/request. Everything else
here powers the central Hub SPA.
"""
import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from task_hub.api.utils import (
    gate_read, can_edit_ticket, normalize_portal,
    VALID_TYPES, VALID_PRIORITIES, VALID_STATUSES,
)


LIST_FIELDS = [
    "name", "title", "ticket_type", "priority", "status",
    "source_portal", "department", "reported_by", "assigned_to",
    "due_date", "sla_deadline", "sla_breached", "resolved_on",
    "linked_label", "linked_url", "creation", "modified",
]


def _as_dict(payload):
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return {}
    return payload or {}


# --------------------------------------------------------------------- create
@frappe.whitelist()
def create_ticket(**kwargs):
    """Universal ticket creation — called by every portal.

    Accepts either flat kwargs or a single `payload` JSON blob. Recognised
    keys: title, description, ticket_type, priority, source_portal,
    department, assigned_to, due_date, tags, linked_doctype, linked_name,
    linked_label, linked_url.
    """
    gate_read()
    data = _as_dict(kwargs.get("payload")) if kwargs.get("payload") else dict(kwargs)

    title = (data.get("title") or "").strip()
    if not title:
        frappe.throw(_("A ticket title is required."))

    ticket_type = data.get("ticket_type") if data.get("ticket_type") in VALID_TYPES else "Task"
    priority = data.get("priority") if data.get("priority") in VALID_PRIORITIES else "Medium"

    doc = frappe.new_doc("Hub Ticket")
    doc.title = title[:180]
    doc.description = data.get("description") or ""
    doc.ticket_type = ticket_type
    doc.priority = priority
    doc.source_portal = normalize_portal(data.get("source_portal"))
    doc.department = data.get("department") or None
    doc.assigned_to = data.get("assigned_to") or None
    doc.due_date = data.get("due_date") or None
    doc.tags = data.get("tags") or None
    doc.linked_doctype = data.get("linked_doctype") or None
    doc.linked_name = data.get("linked_name") or None
    doc.linked_label = data.get("linked_label") or None
    doc.linked_url = data.get("linked_url") or None
    doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"name": doc.name, "title": doc.title, "status": doc.status}


# ----------------------------------------------------------------------- read
@frappe.whitelist()
def list_tickets(status=None, priority=None, source_portal=None,
                 assigned_to=None, reported_by=None, ticket_type=None,
                 search=None, breached_only=0, mine=0,
                 limit=100, start=0, order_by="modified desc"):
    """Filtered ticket list for the Hub board / list views."""
    gate_read()
    filters = {}
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    if source_portal:
        filters["source_portal"] = source_portal
    if ticket_type:
        filters["ticket_type"] = ticket_type
    if assigned_to:
        filters["assigned_to"] = assigned_to
    if reported_by:
        filters["reported_by"] = reported_by
    if int(breached_only or 0):
        filters["sla_breached"] = 1
    if int(mine or 0):
        filters["assigned_to"] = frappe.session.user

    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = {"title": ["like", like], "name": ["like", like]}

    # Whitelist order_by to avoid injection through the SPA.
    allowed_order = {
        "modified desc", "modified asc", "creation desc", "creation asc",
        "priority asc", "due_date asc", "sla_deadline asc",
    }
    order_by = order_by if order_by in allowed_order else "modified desc"

    rows = frappe.get_all(
        "Hub Ticket", filters=filters, or_filters=or_filters,
        fields=LIST_FIELDS, limit_page_length=int(limit),
        limit_start=int(start), order_by=order_by,
    )
    total = frappe.db.count("Hub Ticket", filters=filters)
    return {"tickets": rows, "total": total}


@frappe.whitelist()
def get_ticket(name):
    """Full ticket incl. comments + activity timeline."""
    gate_read()
    doc = frappe.get_doc("Hub Ticket", name)
    d = doc.as_dict()
    return {
        "ticket": {k: d.get(k) for k in (LIST_FIELDS + [
            "description", "tags", "linked_doctype", "linked_name",
        ])},
        "comments": [
            {"author": c.author, "comment_on": c.comment_on, "message": c.message}
            for c in doc.comments
        ],
        "activity": [
            {"activity_on": a.activity_on, "actor": a.actor,
             "action": a.action, "detail": a.detail}
            for a in doc.activity
        ],
    }


# --------------------------------------------------------------------- mutate
def _load_editable(name):
    doc = frappe.get_doc("Hub Ticket", name)
    if not can_edit_ticket(doc):
        frappe.throw(_("You can't modify this ticket."), frappe.PermissionError)
    return doc


@frappe.whitelist()
def update_status(name, status):
    gate_read()
    if status not in VALID_STATUSES:
        frappe.throw(_("Invalid status: {0}").format(status))
    doc = _load_editable(name)
    doc.status = status
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status, "resolved_on": doc.resolved_on}


@frappe.whitelist()
def assign_ticket(name, assigned_to=None):
    gate_read()
    doc = _load_editable(name)
    if assigned_to and not frappe.db.exists("User", assigned_to):
        frappe.throw(_("Unknown user: {0}").format(assigned_to))
    doc.assigned_to = assigned_to or None
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "assigned_to": doc.assigned_to}


@frappe.whitelist()
def set_priority(name, priority):
    gate_read()
    if priority not in VALID_PRIORITIES:
        frappe.throw(_("Invalid priority: {0}").format(priority))
    doc = _load_editable(name)
    doc.priority = priority
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "priority": doc.priority, "sla_deadline": doc.sla_deadline}


@frappe.whitelist()
def add_comment(name, message):
    gate_read()
    message = (message or "").strip()
    if not message:
        frappe.throw(_("Comment cannot be empty."))
    doc = frappe.get_doc("Hub Ticket", name)  # any hub member may comment
    doc.append("comments", {
        "author": frappe.session.user,
        "comment_on": now_datetime(),
        "message": message[:2000],
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "count": len(doc.comments)}
