"""Read-only bridge to core ERPNext Tasks (the Purchasing portal's
Selections workflow) so purchasing work is visible inside the Hub without
migrating or duplicating it."""
import json

import frappe
from frappe import _

from task_hub.api.utils import gate_read, can_view_all


def _may_view():
    """Managers, or members of a Purchase-department workspace."""
    if can_view_all():
        return True
    from task_hub.task_hub.doctype.hub_workspace.hub_workspace import workspace_members
    user = frappe.session.user
    for ws in frappe.get_all("Hub Workspace",
                             filters={"department": ["like", "Purchase%"]},
                             pluck="name"):
        if user in workspace_members(ws):
            return True
    return False


@frappe.whitelist()
def list_selection_tasks(status=None, search=None, limit=100, start=0):
    gate_read()
    if not _may_view():
        frappe.throw(_("Only Task Hub managers and the purchasing team can view ERP tasks."),
                     frappe.PermissionError)

    filters = {}
    if status == "open":
        filters["status"] = ["not in", ("Completed", "Cancelled")]
    elif status:
        filters["status"] = status
    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = {"subject": ["like", like], "name": ["like", like]}

    rows = frappe.get_all(
        "Task", filters=filters, or_filters=or_filters,
        fields=["name", "subject", "status", "priority", "exp_end_date",
                "_assign", "modified"],
        limit_page_length=int(limit), limit_start=int(start),
        order_by="modified desc",
    )
    total = frappe.db.count("Task", filters=filters)
    for r in rows:
        try:
            r["assignees"] = json.loads(r.pop("_assign") or "[]")
        except Exception:
            r["assignees"] = []
    return {"tasks": rows, "total": total}
