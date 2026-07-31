"""Shared helpers for the Task Hub API — role gates, company, portal maps."""
import frappe
from frappe import _


# Anyone in the org can raise a ticket; these roles are the ones we recognise
# as Task Hub participants for read/triage. Existing portal manager roles are
# included so a Purchase/Logistics manager sees their department's tickets
# without a separate grant.
HUB_ROLES = {
    "Task Hub Admin", "Task Hub Manager", "Task Hub Agent", "Task Hub User",
    "System Manager",
}

MANAGER_ROLES = {
    "Task Hub Admin", "Task Hub Manager", "System Manager",
    # Cross-portal department heads get manager-level visibility.
    "Purchase Manager", "Accounts Manager", "Logistics Manager", "Stock Manager",
}

VALID_PORTALS = {"Supplier", "Accounting", "Logistics", "Purchasing", "JoyAgent",
                 "Website", "Mobile App", "Other"}
VALID_TYPES = {"Task", "Problem", "Request"}
VALID_PRIORITIES = {"Urgent", "High", "Medium", "Low"}
VALID_STATUSES = {"Open", "In Progress", "In Review", "Resolved", "Closed", "Cancelled"}


def current_user():
    return frappe.session.user


def is_manager(user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return bool(set(frappe.get_roles(user)) & MANAGER_ROLES)


def gate_read():
    """Any authenticated user may read the hub; Guests are rejected."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to access the Task Hub."), frappe.PermissionError)


def gate_manager():
    if not is_manager():
        frappe.throw(_("Only Task Hub managers can perform this action."),
                     frappe.PermissionError)


def can_view_all(user=None):
    """Managers/admins see the whole hub; everyone else only their own work."""
    return is_manager(user)


def visibility_sql(user=None):
    """WHERE fragment + params scoping rows to the user's own tickets —
    reporter, assignee, or watcher. Empty for managers (they see all).

    Watcher matching is exact set membership, not a substring LIKE: the
    latter leaked every ticket watched by `khali@` to `ali@`.
    """
    user = user or frappe.session.user
    if can_view_all(user):
        return "", {}
    return (
        " AND (reported_by = %(vis_user)s OR assigned_to = %(vis_user)s"
        " OR FIND_IN_SET(%(vis_user)s,"
        " REPLACE(COALESCE(watchers, ''), ', ', ',')))",
        {"vis_user": user},
    )


def can_view_ticket(doc):
    """Managers, the reporter, the assignee, and watchers may open a ticket."""
    if can_view_all():
        return True
    user = frappe.session.user
    if user in (doc.reported_by, doc.assigned_to):
        return True
    try:
        return user in doc.watcher_list()
    except Exception:
        return False


def gate_view(doc):
    """Raise unless the caller may see this ticket. Every endpoint that
    reads or writes ticket content must pass through here — read access is
    what watch/comment/attach implicitly grant, so leaving one of them open
    breaks the whole visibility model."""
    if not can_view_ticket(doc):
        frappe.throw(
            _("You can only work on tickets you reported, are assigned to, or watch."),
            frappe.PermissionError)
    return doc


SAFE_URL_SCHEMES = ("http://", "https://", "/")


def safe_url(url):
    """Keep only navigable URLs — a stored `javascript:` value rendered as an
    href would run in the reader's session."""
    url = (url or "").strip()
    if not url:
        return None
    return url if url.startswith(SAFE_URL_SCHEMES) else None


def normalize_portal(value):
    value = (value or "Other").strip().title()
    return value if value in VALID_PORTALS else "Other"


def can_edit_ticket(ticket):
    """A user can edit a ticket if they are a manager, the assignee, or the
    reporter. `ticket` may be a doc or a name."""
    if is_manager():
        return True
    user = frappe.session.user
    if isinstance(ticket, str):
        row = frappe.db.get_value("Hub Ticket", ticket,
                                  ["reported_by", "assigned_to"], as_dict=True) or {}
        return user in (row.get("reported_by"), row.get("assigned_to"))
    return user in (getattr(ticket, "reported_by", None),
                    getattr(ticket, "assigned_to", None))
