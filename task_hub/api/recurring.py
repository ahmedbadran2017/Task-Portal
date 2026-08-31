"""Manage recurring-ticket rules — managers only."""
import frappe
from frappe import _

from task_hub.api.utils import gate_manager

FIELDS = ["name", "title", "active", "frequency", "weekday", "day_of_month",
          "ticket_type", "priority", "source_portal", "assigned_to",
          "description", "last_run"]


@frappe.whitelist()
def list_rules():
    """Manager-only, same as the automation rules: schedule configuration,
    read by nothing but the settings screen."""
    gate_manager()
    return frappe.get_all("Hub Recurring Ticket", fields=FIELDS,
                          order_by="creation desc")


@frappe.whitelist()
def save_rule(**kwargs):
    """Create (no name) or update (with name) a rule."""
    gate_manager()
    name = kwargs.get("name")
    doc = (frappe.get_doc("Hub Recurring Ticket", name)
           if name else frappe.new_doc("Hub Recurring Ticket"))
    for f in ("title", "frequency", "weekday", "ticket_type", "priority",
              "source_portal", "assigned_to", "description"):
        if f in kwargs and kwargs[f] is not None:
            doc.set(f, kwargs[f])
    if "day_of_month" in kwargs and kwargs["day_of_month"]:
        doc.day_of_month = max(1, min(28, int(kwargs["day_of_month"])))
    if "active" in kwargs:
        doc.active = 1 if kwargs["active"] in (1, "1", True, "true") else 0
    if not (doc.title or "").strip():
        frappe.throw(_("The rule needs a ticket title."))
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {f: doc.get(f) for f in FIELDS}


@frappe.whitelist()
def delete_rule(name):
    gate_manager()
    frappe.delete_doc("Hub Recurring Ticket", name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": name}
