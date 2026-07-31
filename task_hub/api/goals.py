"""Quarterly goals per workspace — progress computed live from tickets, so
a goal is a promise the data keeps score on."""
import frappe
from frappe import _
from frappe.utils import nowdate, date_diff

from task_hub.api.utils import gate_manager

FIELDS = ["name", "goal_name", "workspace", "active", "metric", "target_value",
          "period_start", "period_end"]


def _progress(goal):
    conds = ["resolved_on IS NOT NULL",
             "DATE(resolved_on) BETWEEN %(start)s AND %(end)s"]
    params = {"start": goal.period_start, "end": goal.period_end}
    if goal.workspace:
        conds.append("workspace = %(ws)s")
        params["ws"] = goal.workspace
    row = frappe.db.sql(
        f"""SELECT COUNT(*) n, SUM(sla_breached = 0) on_time
            FROM `tabHub Ticket` WHERE {' AND '.join(conds)}""",
        params, as_dict=True,
    )[0]
    if goal.metric == "SLA on-time %":
        current = round(100 * (row.on_time or 0) / row.n) if row.n else 0
    else:
        current = row.n or 0

    total_days = max(1, date_diff(goal.period_end, goal.period_start))
    elapsed = min(max(0, date_diff(nowdate(), goal.period_start)), total_days)
    time_pct = round(100 * elapsed / total_days)
    progress_pct = min(100, round(100 * current / goal.target_value)) if goal.target_value else 0

    if progress_pct >= 100:
        status = "done"
    elif progress_pct + 10 >= time_pct:
        status = "on_track"
    else:
        status = "behind"
    return {"current": current, "progress_pct": progress_pct,
            "time_pct": time_pct, "status": status}


@frappe.whitelist()
def list_goals():
    gate_manager()
    rows = frappe.get_all("Hub Goal", fields=FIELDS,
                          order_by="period_end asc, goal_name asc")
    for r in rows:
        r.update(_progress(frappe._dict(r)))
    return rows


@frappe.whitelist()
def save_goal(**kwargs):
    gate_manager()
    name = kwargs.get("name")
    doc = frappe.get_doc("Hub Goal", name) if name else frappe.new_doc("Hub Goal")
    if not name and kwargs.get("goal_name"):
        doc.goal_name = kwargs["goal_name"].strip()
    for f in ("workspace", "metric", "period_start", "period_end"):
        if f in kwargs and kwargs[f] is not None:
            doc.set(f, kwargs[f] or None)
    if "active" in kwargs:
        doc.active = 1 if kwargs["active"] in (1, "1", True, "true") else 0
    if "target_value" in kwargs and kwargs["target_value"] not in (None, ""):
        doc.target_value = float(kwargs["target_value"])
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def delete_goal(name):
    gate_manager()
    frappe.delete_doc("Hub Goal", name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": name}
