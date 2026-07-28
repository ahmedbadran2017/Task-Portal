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


def after_migrate():
    _create_portal_roles()


def _create_portal_roles():
    for role_name in PORTAL_ROLES:
        if not frappe.db.exists("Role", role_name):
            doc = frappe.new_doc("Role")
            doc.role_name = role_name
            doc.desk_access = 1
            doc.insert(ignore_permissions=True)
