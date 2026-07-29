"""
One funnel for every Task Hub notification.

`push()` always writes an in-app Hub Notification and optionally sends an
email — so the bell and the inbox can never drift apart. Failures are logged,
never raised: a broken mail setup must not block ticket operations.
"""
import frappe


def deep_link(ticket_name):
    """URL that opens the hub with this ticket's card popped open."""
    return f"/taskhub/tickets?open={ticket_name}"


def email_footer(ticket_name):
    return (f'<p><a href="{deep_link(ticket_name)}">Open {ticket_name} '
            f"in the Task Hub →</a></p>")


def push(user, ticket, ntype, message, email_subject=None, email_html=None):
    """In-app notification for `user`, plus an email when a subject is given."""
    if not user or user in ("Guest", "Administrator"):
        return
    try:
        frappe.get_doc({
            "doctype": "Hub Notification",
            "for_user": user,
            "ticket": ticket,
            "ntype": ntype,
            "message": (message or "")[:500],
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(message=frappe.get_traceback(),
                         title="task_hub: in-app notification failed")
    if email_subject:
        try:
            frappe.sendmail(
                recipients=[user],
                subject=email_subject,
                message=(email_html or f"<p>{message}</p>") + email_footer(ticket),
            )
        except Exception:
            frappe.log_error(message=frappe.get_traceback(),
                             title="task_hub: notification email failed")
