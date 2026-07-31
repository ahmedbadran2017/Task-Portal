"""CEO command center — live ERP pulse + Hub health in one round-trip.

This is the Hub's home-field advantage: Monday/Asana integrate with the ERP
from outside; we read the same database the orders live in.
"""
import frappe
from frappe.utils import add_days, nowdate

from task_hub.api.utils import gate_manager

OPEN_SQL = "('Open', 'In Progress', 'In Review')"


def _one(query, params=None):
    return frappe.db.sql(query, params or {}, as_dict=True)[0]


@frappe.whitelist()
def get_command_center():
    gate_manager()
    today = nowdate()
    d7 = add_days(today, -7)
    d14 = add_days(today, -14)
    d30 = add_days(today, -30)

    orders_today = _one(
        """SELECT COUNT(*) n, IFNULL(SUM(grand_total), 0) total
           FROM `tabSales Order` WHERE docstatus = 1 AND transaction_date = %(d)s""",
        {"d": today})
    orders_7d = _one(
        """SELECT COUNT(*) n FROM `tabSales Order`
           WHERE docstatus = 1 AND transaction_date >= %(d)s""", {"d": d7})
    deliveries_today = _one(
        """SELECT COUNT(*) n FROM `tabDelivery Note`
           WHERE docstatus = 1 AND posting_date = %(d)s""", {"d": today})
    invoices_today = _one(
        """SELECT COUNT(*) n, IFNULL(SUM(grand_total), 0) total
           FROM `tabSales Invoice` WHERE docstatus = 1 AND posting_date = %(d)s""",
        {"d": today})
    overdue_invoices = _one(
        """SELECT COUNT(*) n, IFNULL(SUM(outstanding_amount), 0) total
           FROM `tabSales Invoice`
           WHERE docstatus = 1 AND outstanding_amount > 0.5 AND due_date < %(d)s""",
        {"d": today})
    stuck_orders = _one(
        """SELECT COUNT(*) n FROM `tabSales Order`
           WHERE docstatus = 1 AND status IN ('To Deliver', 'To Deliver and Bill')
             AND transaction_date <= %(d)s""",
        {"d": add_days(today, -3)})
    items_missing_content = _one(
        """SELECT COUNT(*) n FROM `tabItem`
           WHERE disabled = 0 AND creation >= %(d)s
             AND (IFNULL(image, '') = '' OR LENGTH(IFNULL(description, '')) < 30)""",
        {"d": d30})

    orders_by_day = frappe.db.sql(
        """SELECT transaction_date d, COUNT(*) n FROM `tabSales Order`
           WHERE docstatus = 1 AND transaction_date >= %(d)s
           GROUP BY transaction_date ORDER BY transaction_date""",
        {"d": d14}, as_dict=True)

    # Hub health per workspace
    ws_meta = {w.name: w for w in frappe.get_all(
        "Hub Workspace", fields=["name", "icon", "color"])}
    ws_rows = frappe.db.sql(
        f"""SELECT workspace, COUNT(*) open, IFNULL(SUM(sla_breached), 0) breached
            FROM `tabHub Ticket` WHERE status IN {OPEN_SQL}
            GROUP BY workspace ORDER BY open DESC""", as_dict=True)
    workspaces = [{
        "name": r.workspace,
        "icon": (ws_meta.get(r.workspace) or {}).get("icon") or "🗂️",
        "color": (ws_meta.get(r.workspace) or {}).get("color") or "#78716c",
        "open": r.open,
        "breached": int(r.breached or 0),
    } for r in ws_rows if r.workspace]

    hub = _one(
        f"""SELECT
              SUM(status IN {OPEN_SQL}) open,
              SUM(status IN {OPEN_SQL} AND sla_breached = 1) breached,
              SUM(linked_doctype = 'JoyAgent Conversation'
                  AND status IN {OPEN_SQL}) joyagent_open
            FROM `tabHub Ticket`""")
    avg_res = _one(
        """SELECT ROUND(AVG(TIMESTAMPDIFF(HOUR, creation, resolved_on)), 1) h
           FROM `tabHub Ticket`
           WHERE resolved_on IS NOT NULL AND resolved_on >= %(d)s""", {"d": d7})

    return {
        "as_of": str(frappe.utils.now_datetime()),
        "orders_today": orders_today,
        "orders_7d": orders_7d,
        "deliveries_today": deliveries_today,
        "invoices_today": invoices_today,
        "overdue_invoices": overdue_invoices,
        "stuck_orders": stuck_orders,
        "items_missing_content": items_missing_content,
        "orders_by_day": orders_by_day,
        "workspaces": workspaces,
        "hub": {
            "open": int(hub.open or 0),
            "breached": int(hub.breached or 0),
            "joyagent_open": int(hub.joyagent_open or 0),
            "avg_resolution_7d": avg_res.h,
        },
    }
