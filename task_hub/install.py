import frappe

# Roles that own the Task Hub. Desk access so managers can also open records in
# the standard Frappe desk if they want; the SPA is the primary surface.
PORTAL_ROLES = [
    "Task Hub Admin",    # full control across every department
    "Task Hub Manager",  # triage + assign within their department
    "Task Hub Agent",    # work assigned tickets, comment, resolve
    "Task Hub User",     # report problems / create tasks, see their own
]


def after_install():
    _create_portal_roles()
    _ensure_default_workspace()


def after_migrate():
    _create_portal_roles()
    _ensure_default_workspace()


def _create_portal_roles():
    for role_name in PORTAL_ROLES:
        if not frappe.db.exists("Role", role_name):
            doc = frappe.new_doc("Role")
            doc.role_name = role_name
            doc.desk_access = 1
            doc.insert(ignore_permissions=True)


def _ensure_default_workspace():
    try:
        from task_hub.task_hub.doctype.hub_workspace.hub_workspace import (
            ensure_default_workspace)
        ensure_default_workspace()
    except Exception:
        pass  # doctype not migrated yet on first pass
