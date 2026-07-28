"""department was a free-text label ("Logistics & Fulfilment") before it became
a Link to Department. Clear values that aren't real departments, then re-stamp
every ticket from its reporter's Employee record / portal fallback."""
import frappe


def execute():
    if not frappe.db.table_exists("Hub Ticket"):
        return
    from task_hub.task_hub.doctype.hub_ticket.hub_ticket import (
        PORTAL_DEPARTMENT, resolve_user_department)

    rows = frappe.get_all("Hub Ticket",
                          fields=["name", "department", "reported_by", "source_portal"])
    for r in rows:
        dept = r.department if (r.department and
                                frappe.db.exists("Department", r.department)) else None
        if not dept:
            dept = resolve_user_department(r.reported_by)
        if not dept:
            fallback = PORTAL_DEPARTMENT.get(r.source_portal or "Other")
            if fallback and frappe.db.exists("Department", fallback):
                dept = fallback
        if dept != r.department:
            frappe.db.set_value("Hub Ticket", r.name, "department", dept,
                                update_modified=False)
    frappe.db.commit()
