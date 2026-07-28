"""Session / identity endpoints for the Task Hub SPA."""
import frappe

from task_hub.api.utils import gate_read, is_manager, HUB_ROLES


@frappe.whitelist()
def whoami():
    """Return the signed-in user's identity + hub capabilities for the SPA shell."""
    gate_read()
    from task_hub.task_hub.doctype.hub_ticket.hub_ticket import resolve_user_department

    user = frappe.session.user
    roles = list(frappe.get_roles(user))
    return {
        "user_id": user,
        "full_name": frappe.utils.get_fullname(user) or user,
        "user_image": frappe.db.get_value("User", user, "user_image") or "",
        "roles": roles,
        "is_manager": is_manager(user),
        "is_hub_member": bool(set(roles) & HUB_ROLES) or user == "Administrator",
        "company": frappe.defaults.get_user_default("Company") or "Justyol Morocco",
        "department": resolve_user_department(user),
    }


@frappe.whitelist()
def assignable_users(search=None, limit=20):
    """Users a ticket can be assigned to — enabled System Users only.
    Feeds the assignee picker in the SPA."""
    gate_read()
    filters = {"enabled": 1, "user_type": "System User"}
    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = {"full_name": ["like", like], "name": ["like", like]}
    rows = frappe.get_all(
        "User", filters=filters, or_filters=or_filters,
        fields=["name", "full_name", "user_image"],
        limit_page_length=int(limit), order_by="full_name asc",
    )
    return [r for r in rows if r.name not in ("Guest", "Administrator")]
