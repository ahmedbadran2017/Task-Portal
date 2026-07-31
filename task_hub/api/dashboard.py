"""Aggregate metrics for the Task Hub dashboard.

Every query carries the visibility fragment: managers aggregate the whole
company, everyone else only their own tickets (reporter/assignee/watcher).
"""
import frappe
from frappe.utils import add_days, nowdate

from task_hub.api.utils import gate_read, visibility_sql

OPEN_STATES = ("Open", "In Progress", "In Review")
OPEN_SQL = "('Open', 'In Progress', 'In Review')"


@frappe.whitelist()
def get_summary():
    """Headline counts: open work, breaches, my queue, and per-portal / per-status
    / per-priority breakdowns — everything the dashboard needs in one round-trip."""
    gate_read()
    user = frappe.session.user
    vis, params = visibility_sql()

    def count(extra="", more=None):
        p = dict(params, **(more or {}))
        return frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabHub Ticket` WHERE 1=1{vis}{extra}", p,
        )[0][0]

    total = count()
    open_count = count(f" AND status IN {OPEN_SQL}")
    breached = count(f" AND status IN {OPEN_SQL} AND sla_breached = 1")
    resolved = count(" AND status IN ('Resolved', 'Closed')")
    mine_open = count(f" AND status IN {OPEN_SQL} AND assigned_to = %(me)s",
                      {"me": user})
    reported_open = count(f" AND status IN {OPEN_SQL} AND reported_by = %(me)s",
                          {"me": user})
    unassigned = count(f" AND status IN {OPEN_SQL} AND COALESCE(assigned_to, '') = ''")

    by_portal = frappe.db.sql(
        f"""SELECT source_portal AS portal, COUNT(*) AS count
            FROM `tabHub Ticket` WHERE status IN {OPEN_SQL}{vis}
            GROUP BY source_portal ORDER BY count DESC""",
        params, as_dict=True,
    )
    by_status = frappe.db.sql(
        f"""SELECT status, COUNT(*) AS count FROM `tabHub Ticket`
            WHERE 1=1{vis} GROUP BY status""",
        params, as_dict=True,
    )
    by_priority = frappe.db.sql(
        f"""SELECT priority, COUNT(*) AS count FROM `tabHub Ticket`
            WHERE status IN {OPEN_SQL}{vis} GROUP BY priority""",
        params, as_dict=True,
    )

    return {
        "totals": {
            "total": total,
            "open": open_count,
            "breached": breached,
            "resolved": resolved,
            "mine_open": mine_open,
            "reported_open": reported_open,
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
    vis, vparams = visibility_sql()

    created = frappe.db.sql(
        f"""SELECT YEARWEEK(creation, 3) yw, MIN(DATE(creation)) start, COUNT(*) n
            FROM `tabHub Ticket` WHERE creation >= %(from)s{vis} GROUP BY yw""",
        dict(vparams, **{"from": start}), as_dict=True,
    )
    resolved = frappe.db.sql(
        f"""SELECT YEARWEEK(resolved_on, 3) yw, COUNT(*) n
            FROM `tabHub Ticket`
            WHERE resolved_on IS NOT NULL AND resolved_on >= %(from)s{vis}
            GROUP BY yw""",
        dict(vparams, **{"from": start}), as_dict=True,
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

    # Per-portal health, last 30 days for the resolution metrics. Two grouped
    # queries instead of three per portal — the old loop cost 24 full scans.
    month_ago = add_days(nowdate(), -30)
    open_rows = frappe.db.sql(
        f"""SELECT source_portal p, COUNT(*) open_now,
                   IFNULL(SUM(sla_breached), 0) breached
            FROM `tabHub Ticket` WHERE status IN {OPEN_SQL}{vis}
            GROUP BY source_portal""",
        vparams, as_dict=True,
    )
    res_rows = frappe.db.sql(
        f"""SELECT source_portal p, COUNT(*) n,
                   AVG(TIMESTAMPDIFF(HOUR, creation, resolved_on)) avg_h
            FROM `tabHub Ticket`
            WHERE resolved_on IS NOT NULL AND resolved_on >= %(month_ago)s{vis}
            GROUP BY source_portal""",
        dict(vparams, month_ago=month_ago), as_dict=True,
    )
    open_map = {r.p: r for r in open_rows}
    res_map = {r.p: r for r in res_rows}

    health = []
    for p in ("Supplier", "Accounting", "Logistics", "Purchasing", "JoyAgent",
              "Website", "Mobile App", "Other"):
        o = open_map.get(p)
        r = res_map.get(p)
        open_now = int(o.open_now) if o else 0
        breached = int(o.breached or 0) if o else 0
        resolved_30d = int(r.n) if r else 0
        if not any((open_now, breached, resolved_30d)):
            continue
        health.append({
            "portal": p,
            "open": open_now,
            "breached": breached,
            "resolved_30d": resolved_30d,
            "avg_resolution_hours": round(r.avg_h, 1) if (r and r.avg_h) else None,
        })

    return {"series": series, "health": health}
