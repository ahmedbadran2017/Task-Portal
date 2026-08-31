"""
One funnel for every Task Hub notification.

`push()` always writes an in-app Hub Notification and optionally sends an
email — so the bell and the inbox can never drift apart. Failures are logged,
never raised: a broken mail setup must not block ticket operations.
"""
import re
from urllib.parse import quote

import frappe

# A bench that hasn't been flagged as production (no restart_supervisor_on_update
# / restart_systemd_on_update in common_site_config) makes Frappe's get_url()
# append the bench webserver port. Mail is sent from the scheduler, where there
# is no request to borrow a real host from, so every link went out as
# https://admin.justyol.com:8000/... — a port nothing serves publicly.
DEFAULT_WEBSERVER_PORT = "8000"


def _strip_dev_port(url):
    """Drop a bench dev port from a real hostname; keep it for localhost."""
    m = re.match(r"^(https?://)([^/:]+)(?::(\d+))?(.*)$", url or "")
    if not m:
        return url
    scheme, host, port, rest = m.groups()
    if not port:
        return url
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".localhost"):
        return url
    conf = frappe.conf or {}
    dev_ports = {str(conf.get("webserver_port") or DEFAULT_WEBSERVER_PORT),
                 str(conf.get("http_port") or "")} - {""}
    return f"{scheme}{host}{rest}" if port in dev_ports else url


def base_url():
    """Absolute origin for links that leave the browser.

    Prefers what the site was explicitly told to call itself, so emails don't
    depend on how the bench happens to be flagged. `task_hub_url` overrides
    for the odd case where the hub lives behind a different host than the desk.
    """
    conf = frappe.conf or {}
    explicit = str(conf.get("task_hub_url") or conf.get("host_name") or "").strip()
    explicit = explicit.rstrip("/")
    if explicit:
        if not explicit.startswith(("http://", "https://")):
            explicit = "https://" + explicit
        return explicit
    try:
        from frappe.utils import get_url
        return _strip_dev_port((get_url() or "").rstrip("/"))
    except Exception:
        return ""


def hub_url(path="/taskhub"):
    """Absolute URL into the SPA. Relative hrefs have no base inside a mail
    client, so every link that ships in an email must go through here."""
    if not path.startswith("/"):
        path = "/" + path
    return base_url() + path


def deep_link(ticket_name):
    """URL that opens the hub with this ticket's card popped open."""
    return hub_url(f"/taskhub/tickets?open={quote(str(ticket_name or ''), safe='')}")


def email_footer(ticket_name):
    return (f'<p><a href="{deep_link(ticket_name)}">Open {ticket_name} '
            f"in the Task Hub →</a></p>")


def push(user, ticket, ntype, message, email_subject=None, email_html=None):
    """In-app notification for `user`, plus an email when a subject is given.
    Administrator gets in-app entries (useful while testing) but never email —
    its address is typically not a real mailbox."""
    if not user or user == "Guest":
        return
    if user == "Administrator":
        email_subject = None
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
