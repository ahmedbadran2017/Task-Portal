"""
Performance scorecards — the numbers behind "how is each team actually doing".

Department scorecard (per real ERPNext Department):
    members, open, breached_open, created_Nd, resolved_Nd,
    avg_resolution_hours, sla_compliance_pct
Employee scorecard (per assignee, optionally inside one department):
    same resolution metrics per person + current load.
"""
import frappe
from frappe.utils import add_days, nowdate, cint

from task_hub.api.utils import gate_manager

OPEN_STATES = ("Open", "In Progress", "In Review")


def _period(days):
    days = max(7, min(365, cint(days) or 30))
    return add_days(nowdate(), -days), days


@frappe.whitelist()
def department_scorecard(days=30):
    """One row per department that has employees or tickets."""
    gate_manager()
    since, days = _period(days)

    # Active headcount per department.
    members = {r.department: r.n for r in frappe.db.sql(
        """SELECT department, COUNT(*) n FROM `tabEmployee`
           WHERE status = 'Active' AND department IS NOT NULL
           GROUP BY department""", as_dict=True)}

    # Current load.
    load = {r.department: r for r in frappe.db.sql(
        """SELECT department,
                  COUNT(*) open_now,
                  SUM(sla_breached = 1) breached
           FROM `tabHub Ticket`
           WHERE status IN %(open)s AND department IS NOT NULL
           GROUP BY department""",
        {"open": OPEN_STATES}, as_dict=True)}

    # Throughput inside the period.
    created = {r.department: r.n for r in frappe.db.sql(
        """SELECT department, COUNT(*) n FROM `tabHub Ticket`
           WHERE creation >= %(since)s AND department IS NOT NULL
           GROUP BY department""", {"since": since}, as_dict=True)}
    resolved = {r.department: r for r in frappe.db.sql(
        """SELECT department,
                  COUNT(*) n,
                  AVG(TIMESTAMPDIFF(HOUR, creation, resolved_on)) avg_h,
                  SUM(sla_deadline IS NOT NULL AND resolved_on <= sla_deadline) on_time
           FROM `tabHub Ticket`
           WHERE resolved_on IS NOT NULL AND resolved_on >= %(since)s
             AND department IS NOT NULL
           GROUP BY department""", {"since": since}, as_dict=True)}

    depts = sorted(set(members) | set(load) | set(created) | set(resolved))
    rows = []
    for d in depts:
        res = resolved.get(d)
        ld = load.get(d)
        rows.append({
            "department": d,
            "members": members.get(d, 0),
            "open": (ld and cint(ld.open_now)) or 0,
            "breached": (ld and cint(ld.breached)) or 0,
            "created": created.get(d, 0),
            "resolved": (res and cint(res.n)) or 0,
            "avg_resolution_hours": round(res.avg_h, 1) if res and res.avg_h else None,
            "sla_compliance_pct": (
                round(100 * cint(res.on_time) / cint(res.n)) if res and cint(res.n) else None
            ),
        })
    # Most loaded first; quiet departments (no members, no activity) drop out.
    rows = [r for r in rows if r["members"] or r["open"] or r["created"] or r["resolved"]]
    rows.sort(key=lambda r: (-r["open"], -r["resolved"]))
    return {"days": days, "departments": rows}


@frappe.whitelist()
def workspace_scorecard(days=30):
    """One row per workspace — the same health metrics, cut by workspace."""
    gate_manager()
    since, days = _period(days)

    load = {r.workspace: r for r in frappe.db.sql(
        """SELECT workspace, COUNT(*) open_now, SUM(sla_breached = 1) breached
           FROM `tabHub Ticket`
           WHERE status IN %(open)s AND workspace IS NOT NULL
           GROUP BY workspace""", {"open": OPEN_STATES}, as_dict=True)}
    created = {r.workspace: r.n for r in frappe.db.sql(
        """SELECT workspace, COUNT(*) n FROM `tabHub Ticket`
           WHERE creation >= %(since)s AND workspace IS NOT NULL
           GROUP BY workspace""", {"since": since}, as_dict=True)}
    resolved = {r.workspace: r for r in frappe.db.sql(
        """SELECT workspace, COUNT(*) n,
                  AVG(TIMESTAMPDIFF(HOUR, creation, resolved_on)) avg_h,
                  SUM(sla_deadline IS NOT NULL AND resolved_on <= sla_deadline) on_time
           FROM `tabHub Ticket`
           WHERE resolved_on IS NOT NULL AND resolved_on >= %(since)s
             AND workspace IS NOT NULL
           GROUP BY workspace""", {"since": since}, as_dict=True)}

    from task_hub.task_hub.doctype.hub_workspace.hub_workspace import workspace_members
    rows = []
    for name in frappe.get_all("Hub Workspace", pluck="name",
                               order_by="is_default desc, creation asc"):
        ws = frappe.get_cached_doc("Hub Workspace", name)
        res, ld = resolved.get(name), load.get(name)
        rows.append({
            "workspace": name,
            "icon": ws.icon or "🗂️",
            "color": ws.color or "#d45d3e",
            "use_sla": ws.use_sla,
            "members": len(workspace_members(name)),
            "open": (ld and cint(ld.open_now)) or 0,
            "breached": (ld and cint(ld.breached)) or 0,
            "created": created.get(name, 0),
            "resolved": (res and cint(res.n)) or 0,
            "avg_resolution_hours": round(res.avg_h, 1) if res and res.avg_h else None,
            "sla_compliance_pct": (
                round(100 * cint(res.on_time) / cint(res.n)) if res and cint(res.n) else None
            ),
        })
    rows.sort(key=lambda r: (-r["open"], -r["resolved"]))
    return {"days": days, "workspaces": rows}


@frappe.whitelist()
def employee_scorecard(days=30, department=None, workspace=None):
    """One row per person. With `department`, covers that team's employees;
    with `workspace`, covers its members with stats scoped to that
    workspace's tickets; otherwise everyone who has tickets."""
    gate_manager()
    since, days = _period(days)

    params = {"since": since, "open": OPEN_STATES}
    ws_cond = ""
    if workspace:
        params["ws"] = workspace
        ws_cond = " AND workspace = %(ws)s"
    if department:
        params["dept"] = department

    # Current load per assignee.
    load = {r.assigned_to: r for r in frappe.db.sql(
        f"""SELECT assigned_to,
                  COUNT(*) open_now,
                  SUM(sla_breached = 1) breached
           FROM `tabHub Ticket`
           WHERE status IN %(open)s AND assigned_to IS NOT NULL{ws_cond}
           GROUP BY assigned_to""", params, as_dict=True)}

    resolved = {r.assigned_to: r for r in frappe.db.sql(
        f"""SELECT assigned_to,
                  COUNT(*) n,
                  AVG(TIMESTAMPDIFF(HOUR, creation, resolved_on)) avg_h,
                  SUM(sla_deadline IS NOT NULL AND resolved_on <= sla_deadline) on_time
           FROM `tabHub Ticket`
           WHERE resolved_on IS NOT NULL AND resolved_on >= %(since)s
             AND assigned_to IS NOT NULL{ws_cond}
           GROUP BY assigned_to""", params, as_dict=True)}

    reported = {r.reported_by: r.n for r in frappe.db.sql(
        f"""SELECT reported_by, COUNT(*) n FROM `tabHub Ticket`
           WHERE creation >= %(since)s AND reported_by IS NOT NULL{ws_cond}
           GROUP BY reported_by""", params, as_dict=True)}

    if workspace:
        from task_hub.task_hub.doctype.hub_workspace.hub_workspace import workspace_members
        member_ids = workspace_members(workspace)
        names_map = {r.user_id: r.employee_name for r in frappe.get_all(
            "Employee", filters={"user_id": ["in", member_ids or [""]]},
            fields=["user_id", "employee_name"])}
        users = {u: names_map.get(u) for u in member_ids}
    elif department:
        base_users = frappe.db.sql(
            """SELECT user_id, employee_name FROM `tabEmployee`
               WHERE status = 'Active' AND department = %(dept)s
                 AND user_id IS NOT NULL""", params, as_dict=True)
        users = {r.user_id: r.employee_name for r in base_users}
    else:
        users = {}
        for u in set(load) | set(resolved):
            users[u] = None

    # Resolve display names in one query.
    if users:
        names = {r.name: r.full_name for r in frappe.get_all(
            "User", filters={"name": ["in", list(users)]},
            fields=["name", "full_name"])}
    else:
        names = {}

    rows = []
    for u, emp_name in users.items():
        ld, res = load.get(u), resolved.get(u)
        rows.append({
            "user": u,
            "full_name": emp_name or names.get(u) or u.split("@")[0],
            "open": (ld and cint(ld.open_now)) or 0,
            "breached": (ld and cint(ld.breached)) or 0,
            "resolved": (res and cint(res.n)) or 0,
            "reported": reported.get(u, 0),
            "avg_resolution_hours": round(res.avg_h, 1) if res and res.avg_h else None,
            "sla_compliance_pct": (
                round(100 * cint(res.on_time) / cint(res.n)) if res and cint(res.n) else None
            ),
        })
    rows.sort(key=lambda r: (-r["resolved"], -r["open"]))
    return {"days": days, "department": department, "employees": rows}
