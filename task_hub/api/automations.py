"""CRUD for user-defined automation rules (the engine lives in the
Hub Automation Rule controller)."""
import frappe
from frappe import _

from task_hub.api.utils import gate_manager

FIELDS = ["name", "rule_name", "active", "workspace", "trigger", "stuck_days",
          "action", "action_user", "action_priority"]


@frappe.whitelist()
def list_rules():
    """Manager-only: this is the rule engine's configuration — which boards it
    watches, who it assigns work to — and only the settings screen reads it."""
    gate_manager()
    return frappe.get_all("Hub Automation Rule", fields=FIELDS,
                          order_by="rule_name asc")


@frappe.whitelist()
def save_rule(**kwargs):
    gate_manager()
    name = kwargs.get("name")
    doc = (frappe.get_doc("Hub Automation Rule", name)
           if name else frappe.new_doc("Hub Automation Rule"))
    if not name and kwargs.get("rule_name"):
        doc.rule_name = kwargs["rule_name"].strip()
    for f in ("workspace", "trigger", "action", "action_user", "action_priority"):
        if f in kwargs and kwargs[f] is not None:
            doc.set(f, kwargs[f] or None)
    if "active" in kwargs:
        doc.active = 1 if kwargs["active"] in (1, "1", True, "true") else 0
    if "stuck_days" in kwargs and kwargs["stuck_days"] not in (None, ""):
        doc.stuck_days = int(kwargs["stuck_days"])
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def delete_rule(name):
    gate_manager()
    frappe.delete_doc("Hub Automation Rule", name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": name}
