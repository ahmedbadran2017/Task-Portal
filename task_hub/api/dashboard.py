"""Aggregate metrics for the Task Hub dashboard."""
import frappe
from frappe.utils import add_days, nowdate, getdate

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


@frappe.whitelist()
def get_trends(weeks=8):
    """Created-vs-resolved per ISO week + per-portal health, for the roll-up."""
    gate_read()
    weeks = max(2, min(26, int(weeks or 8)))
    start = add_days(nowdate(), -7 * weeks)

    created = frappe.db.sql(
        """SELECT YEARWEEK(creation, 3) yw, MIN(DATE(creation)) start, COUNT(*) n
           FROM `tabHub Ticket` WHERE creation >= %s GROUP BY yw""",
        (start,), as_dict=True,
    )
    resolved = frappe.db.sql(
        """SELECT YEARWEEK(resolved_on, 3) yw, COUNT(*) n
           FROM `tabHub Ticket`
           WHERE resolved_on IS NOT NULL AND resolved_on >= %s GROUP BY yw""",
        (start,), as_dict=True,
    )
    resolved_map = {r.yw: r.n for r in resolved}

    # Build a continuous series keyed on the created weeks plus any
    # resolved-only weeks, sorted chronologically.
    weeks_seen = {}
    for r in created:
        weeks_seen[r.yw] = {"week": str(r.yw), "start": str(r.start),
                            "created": r.n, "resolved": 0}
    for yw, n in resolved_map.items():
        weeks_seen.setdefault(yw, {"week": str(yw), "start": "", "created": 0,
                                   "resolved": 0})
        weeks_seen[yw]["resolved"] = n
    series = [weeks_seen[k] for k in sorted(weeks_seen)]

    # Per-portal health, last 30 days for the resolution metrics.
    month_ago = add_days(nowdate(), -30)
    health = []
    for p in ("Supplier", "Accounting", "Logistics", "Purchasing", "JoyAgent", "Other"):
        open_now = frappe.db.count("Hub Ticket", {
            "source_portal": p, "status": ["in", OPEN_STATES]})
        breached = frappe.db.count("Hub Ticket", {
            "source_portal": p, "status": ["in", OPEN_STATES], "sla_breached": 1})
        row = frappe.db.sql(
            """SELECT COUNT(*) n, AVG(TIMESTAMPDIFF(HOUR, creation, resolved_on)) avg_h
               FROM `tabHub Ticket`
               WHERE source_portal = %s AND resolved_on IS NOT NULL
                 AND resolved_on >= %s""",
            (p, month_ago), as_dict=True,
        )[0]
        if not any((open_now, breached, row.n)):
            continue
        health.append({
            "portal": p,
            "open": open_now,
            "breached": breached,
            "resolved_30d": row.n or 0,
            "avg_resolution_hours": round(row.avg_h, 1) if row.avg_h else None,
        })

    return {"series": series, "health": health}
