"""Shared helpers for the Task Hub API — role gates, company, portal maps."""
import frappe
from frappe import _


# Anyone in the org can raise a ticket; these roles are the ones we recognise
# as Task Hub participants for read/triage.
HUB_ROLES = {
    "Task Hub Admin", "Task Hub Manager", "Task Hub Agent", "Task Hub User",
    "System Manager",
}

# Company-wide sight. Deliberately only the three roles that mean "runs the
# Task Hub" — ERPNext's Purchase/Accounts/Logistics/Stock Manager roles used
# to be here, but they are warehouse and ledger grants handed out for day-to-day
# work, and they were silently buying whoever held them every ticket in the
# company plus every employee's performance record.
#
# Supervising a team is now said explicitly, per board, via `leads` — see
# led_workspaces() below.
MANAGER_ROLES = {
    "Task Hub Admin", "Task Hub Manager", "System Manager",
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


def split_users(value):
    """Comma/newline separated user list → clean list. The doctype stores
    people this way in `watchers`, `extra_members` and `leads` alike."""
    return [u.strip() for u in (value or "").replace("\n", ",").split(",") if u.strip()]


def led_workspaces(user=None):
    """Boards this user supervises. A lead sees their whole board, not just
    the tickets they personally touched — that is the entire point of the
    role, and it is the middle tier between "my own work" and "everything".

    Cached per request: visibility_sql() runs on every list query.
    """
    user = user or frappe.session.user
    cache = getattr(frappe.local, "_th_led_ws", None)
    if cache is None:
        cache = frappe.local._th_led_ws = {}
    if user not in cache:
        try:
            cache[user] = [w.name for w in frappe.get_all(
                "Hub Workspace", fields=["name", "leads"], ignore_permissions=True)
                if user in split_users(w.leads)]
        except Exception:
            # Pre-migration sites have no `leads` column yet; degrade to
            # "own work only" rather than failing every ticket list.
            cache[user] = []
    return cache[user]


def visibility_sql(user=None):
    """WHERE fragment + params scoping rows to what this user may see:
    their own tickets (reporter, assignee, watcher) plus every ticket on a
    board they lead. Empty for managers — they see all.

    Watcher matching is exact set membership, not a substring LIKE: the
    latter leaked every ticket watched by `khali@` to `ali@`.
    """
    user = user or frappe.session.user
    if can_view_all(user):
        return "", {}
    clause = ("reported_by = %(vis_user)s OR assigned_to = %(vis_user)s"
              " OR FIND_IN_SET(%(vis_user)s,"
              " REPLACE(COALESCE(watchers, ''), ', ', ','))")
    params = {"vis_user": user}
    led = led_workspaces(user)
    if led:
        keys = [f"vis_ws{i}" for i in range(len(led))]
        clause += " OR workspace IN (%s)" % ", ".join(f"%({k})s" for k in keys)
        params.update(dict(zip(keys, led)))
    return f" AND ({clause})", params


def can_view_ticket(doc):
    """Managers, the board's leads, the reporter, the assignee, and watchers."""
    if can_view_all():
        return True
    user = frappe.session.user
    if user in (doc.reported_by, doc.assigned_to):
        return True
    if doc.workspace and doc.workspace in led_workspaces(user):
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
            _("You can only work on tickets you reported, are assigned to, watch, "
              "or that sit on a board you lead."),
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


def workspace_tracks_portal(workspace):
    """Does this board ask where work came from?

    Only cross-portal intake (technical support) does. On a department's own
    board the question has no answer, so the field is neither asked for nor
    required. An unknown/missing workspace falls back to the default board's
    setting, which is what such a ticket will land on anyway.
    """
    if workspace:
        value = frappe.db.get_value("Hub Workspace", workspace, "track_source_portal")
        if value is not None:
            return bool(value)
    from task_hub.task_hub.doctype.hub_workspace.hub_workspace import (
        get_default_workspace)
    default = get_default_workspace()
    if not default:
        return True
    return bool(frappe.db.get_value("Hub Workspace", default, "track_source_portal"))


def require_portal(value, workspace=None):
    """Portal is mandatory on the interactive entrypoint — but only on boards
    that track it: whoever raises a support ticket must say where it came
    from, so "Other" is a deliberate choice rather than an accepted default.

    On a board that doesn't track portals the value is dropped rather than
    coerced to "Other", so the portal reports stay honest: an "Other" bucket
    stuffed with design tasks would be worse than no row at all.

    Server-side creators (automations, forms, templates) set the field
    themselves and never come through here.
    """
    value = (value or "").strip().title()
    if not workspace_tracks_portal(workspace):
        return value if value in VALID_PORTALS else None
    if not value:
        frappe.throw(_("Choose which portal this ticket comes from."))
    if value not in VALID_PORTALS:
        frappe.throw(_("'{0}' is not a valid portal.").format(value))
    return value


def can_edit_ticket(ticket):
    """A user can edit a ticket if they are a manager, the assignee, the
    reporter, or a lead of the board it sits on. `ticket` may be a doc or a
    name.

    Leads get edit and not merely sight on purpose: a supervisor who can see a
    ticket stalling on their own board but cannot reassign or re-prioritise it
    is not supervising anything.
    """
    if is_manager():
        return True
    user = frappe.session.user
    if isinstance(ticket, str):
        row = frappe.db.get_value(
            "Hub Ticket", ticket,
            ["reported_by", "assigned_to", "workspace"], as_dict=True) or {}
        workspace = row.get("workspace")
        people = (row.get("reported_by"), row.get("assigned_to"))
    else:
        workspace = getattr(ticket, "workspace", None)
        people = (getattr(ticket, "reported_by", None),
                  getattr(ticket, "assigned_to", None))
    if user in people:
        return True
    return bool(workspace) and workspace in led_workspaces(user)
