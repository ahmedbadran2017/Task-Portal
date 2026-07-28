import frappe

no_cache = 1


def get_context(context):
    """Render the Vue SPA shell. Gate by login, pre-compute shell globals as
    plain Python values so the Jinja sandbox never calls restricted helpers."""
    context.no_cache = 1

    if frappe.session.user == "Guest":
        try:
            path = frappe.request.path or "/taskhub"
            qs = frappe.request.query_string.decode() if frappe.request.query_string else ""
            target = path + ("?" + qs if qs else "")
        except Exception:
            target = "/taskhub"
        frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(target)
        raise frappe.Redirect

    # The hub is open to any signed-in staff member — anyone can raise or view
    # tickets. Fine-grained edit rights are enforced per-method in the API.
    user = frappe.session.user
    try:
        full_name = frappe.utils.get_fullname(user) or ""
    except Exception:
        full_name = ""
    try:
        user_image = frappe.db.get_value("User", user, "user_image") or ""
    except Exception:
        user_image = ""
    try:
        roles = list(frappe.get_roles(user))
    except Exception:
        roles = []
    try:
        company = frappe.defaults.get_user_default("Company") or "Justyol Morocco"
    except Exception:
        company = "Justyol Morocco"
    try:
        csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        csrf_token = ""
    try:
        site_name = frappe.local.site or ""
    except Exception:
        site_name = ""

    context.portal_shell = {
        "csrf_token": csrf_token,
        "site_name": site_name,
        "user_id": user,
        "full_name": full_name,
        "user_image": user_image,
        "user_roles": roles,
        "company": company,
    }
