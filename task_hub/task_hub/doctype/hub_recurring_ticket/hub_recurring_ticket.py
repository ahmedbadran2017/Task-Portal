import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate


class HubRecurringTicket(Document):
    pass


def run_recurring_tickets():
    """Daily scheduler: open a Hub Ticket for every rule that is due today
    and hasn't run yet today."""
    today = getdate(nowdate())
    weekday_name = today.strftime("%A")

    for rule in frappe.get_all(
        "Hub Recurring Ticket", filters={"active": 1},
        fields=["name", "title", "description", "ticket_type", "priority",
                "source_portal", "assigned_to", "frequency", "weekday",
                "day_of_month", "last_run", "owner"],
    ):
        if rule.last_run and getdate(rule.last_run) >= today:
            continue
        due = (
            rule.frequency == "Daily"
            or (rule.frequency == "Weekly" and rule.weekday == weekday_name)
            or (rule.frequency == "Monthly" and int(rule.day_of_month or 1) == today.day)
        )
        if not due:
            continue
        try:
            doc = frappe.new_doc("Hub Ticket")
            doc.title = rule.title
            doc.description = rule.description or ""
            doc.ticket_type = rule.ticket_type or "Task"
            doc.priority = rule.priority or "Medium"
            doc.source_portal = rule.source_portal or "Other"
            doc.assigned_to = rule.assigned_to or None
            doc.auto_generated = 1
            doc.reported_by = rule.owner or "Administrator"
            doc.insert(ignore_permissions=True)
            frappe.db.set_value("Hub Recurring Ticket", rule.name, "last_run",
                                today, update_modified=False)
        except Exception:
            frappe.log_error(message=frappe.get_traceback(),
                             title=f"task_hub: recurring rule {rule.name} failed")
    frappe.db.commit()
