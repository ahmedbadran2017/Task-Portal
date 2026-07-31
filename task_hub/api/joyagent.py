"""JoyAgent → Task Hub bridge.

One click in the WhatsApp desk turns a stuck conversation into a Hub ticket
with the customer, order, and AI summary carried over — so escalations stop
living in agents' heads.
"""
import frappe
from frappe import _

from task_hub.api.utils import gate_read, is_manager

OPEN_STATES = ("Open", "In Progress", "In Review")

# Only the WhatsApp desk (and hub managers) may pull customer data out of a
# conversation — otherwise any signed-in user could enumerate conversation
# IDs and read customer PII back through the ticket they created.
DESK_ROLES = {"JoyAgent Agent", "JoyAgent Content", "Supplier Portal Admin",
              "Agent Manager", "Agent"}


def _gate_desk():
    if is_manager() or (set(frappe.get_roles()) & DESK_ROLES):
        return
    frappe.throw(_("Only the WhatsApp desk team can escalate conversations."),
                 frappe.PermissionError)


@frappe.whitelist()
def escalate_conversation(conversation, note=None):
    """Create (or return the existing open) Hub ticket for a JoyAgent
    conversation. Desk agents and hub managers only."""
    gate_read()
    _gate_desk()
    if not frappe.db.exists("DocType", "JoyAgent Conversation"):
        frappe.throw(_("JoyAgent is not installed on this site."))
    row = frappe.db.get_value(
        "JoyAgent Conversation", conversation,
        ["name", "customer_name", "customer_phone", "category", "status",
         "summary", "linked_sales_order"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Conversation {0} was not found.").format(conversation))

    # One open ticket per conversation — a second click surfaces the first.
    existing = frappe.db.get_value(
        "Hub Ticket",
        {"linked_doctype": "JoyAgent Conversation", "linked_name": row.name,
         "status": ["in", OPEN_STATES]},
        "name",
    )
    if existing:
        # A second agent hitting escalate must be able to open what they're
        # pointed at, so add them as a watcher.
        try:
            doc = frappe.get_doc("Hub Ticket", existing)
            watchers = set(doc.watcher_list()) | {frappe.session.user}
            doc.watchers = ", ".join(sorted(watchers))
            doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            pass
        return {"name": existing, "existing": True}

    who = row.customer_name or row.customer_phone or row.name
    lines = []
    if row.customer_name:
        lines.append(f"Customer: {row.customer_name}")
    if row.customer_phone:
        lines.append(f"Phone: {row.customer_phone}")
    if row.category:
        lines.append(f"Category: {row.category}")
    if row.linked_sales_order:
        lines.append(f"Sales Order: {row.linked_sales_order}")
    if (note or "").strip():
        lines.append(f"\nAgent note:\n{note.strip()[:2000]}")
    if (row.summary or "").strip():
        lines.append(f"\nConversation summary:\n{row.summary.strip()[:3000]}")

    doc = frappe.new_doc("Hub Ticket")
    doc.title = f"WhatsApp escalation: {who}"[:180]
    doc.description = "\n".join(lines)
    doc.ticket_type = "Problem"
    doc.priority = "High"
    doc.source_portal = "JoyAgent"
    doc.linked_doctype = "JoyAgent Conversation"
    doc.linked_name = row.name
    doc.linked_label = f"WhatsApp: {who}"
    doc.linked_url = "/agent"
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "existing": False}
