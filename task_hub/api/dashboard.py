"""Aggregate metrics for the Task Hub dashboard."""
import frappe

from task_hub.api.utils import gate_read

OPEN_STATES = ("Open", "In Progress", "In Review")


@frappe.whitelist()
def get_summary():
    """Headline counts: open work, breaches, my queue, and per-portal / per-status
    / per-priority breakdowns — everything the dashboard needs in one round-trip."""
    gate_read()
    user = frappe.session.user

    def count(filters):
        return frappe.db.count("Hub Ticket", filters=filters)

    total = count({})
    open_count = count({"status": ["in", OPEN_STATES]})
    breached = count({"sla_breached": 1, "status": ["in", OPEN_STATES]})
    resolved = count({"status": ["in", ("Resolved", "Closed")]})
    mine_open = count({"assigned_to": user, "status": ["in", OPEN_STATES]})
    unassigned = count({"assigned_to": ["in", (None, "")], "status": ["in", OPEN_STATES]})

    by_portal = frappe.db.get_all(
        "Hub Ticket", filters={"status": ["in", OPEN_STATES]},
        fields=["source_portal as portal", "count(name) as count"],
        group_by="source_portal", order_by="count desc",
    )
    by_status = frappe.db.get_all(
        "Hub Ticket", fields=["status", "count(name) as count"],
        group_by="status",
    )
    by_priority = frappe.db.get_all(
        "Hub Ticket", filters={"status": ["in", OPEN_STATES]},
        fields=["priority", "count(name) as count"],
        group_by="priority",
    )

    return {
        "totals": {
            "total": total,
            "open": open_count,
            "breached": breached,
            "resolved": resolved,
            "mine_open": mine_open,
            "unassigned": unassigned,
        },
        "by_portal": by_portal,
        "by_status": by_status,
        "by_priority": by_priority,
    }
