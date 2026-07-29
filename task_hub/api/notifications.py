"""In-app notification feed for the bell in the SPA."""
import frappe
from frappe import _

from task_hub.api.utils import gate_read


@frappe.whitelist()
def my_notifications(limit=25):
    """The signed-in user's recent notifications + unread count."""
    gate_read()
    user = frappe.session.user
    rows = frappe.get_all(
        "Hub Notification",
        filters={"for_user": user},
        fields=["name", "ticket", "ntype", "message", "seen", "creation"],
        order_by="creation desc",
        limit_page_length=min(int(limit or 25), 100),
    )
    unread = frappe.db.count("Hub Notification", {"for_user": user, "seen": 0})
    return {"notifications": rows, "unread": unread}


@frappe.whitelist()
def mark_seen(name=None):
    """Mark one notification (or all of mine) as seen."""
    gate_read()
    user = frappe.session.user
    if name:
        row = frappe.db.get_value("Hub Notification", name, ["for_user"], as_dict=True)
        if not row or row.for_user != user:
            frappe.throw(_("Not your notification."), frappe.PermissionError)
        frappe.db.set_value("Hub Notification", name, "seen", 1, update_modified=False)
    else:
        frappe.db.sql(
            "UPDATE `tabHub Notification` SET seen = 1 WHERE for_user = %s AND seen = 0",
            (user,),
        )
    frappe.db.commit()
    return {"unread": frappe.db.count("Hub Notification", {"for_user": user, "seen": 0})}
