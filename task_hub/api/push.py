"""Web Push — the third notification channel, alongside the bell and email.

Everything funnels through `task_hub.notify.push()`, so this module only has
to answer two questions: which devices belong to a user, and does that user
want to be buzzed about this kind of event right now.

Keys live in site_config (never in a doctype):

    bench --site <site> execute task_hub.api.push.generate_vapid_keys

prints a keypair to paste in. The private key signs our pushes; the public key
is handed to the browser so the push service can verify us.
"""
import json
import re
from datetime import datetime, time as dtime

import frappe
from frappe import _
from frappe.utils import now_datetime

from task_hub.api.utils import gate_read

# ntype (as passed to notify.push) -> the preference field that governs it.
# Anything unmapped is treated as opt-in-by-default, so a new notification
# type is never silently swallowed.
NTYPE_PREF = {
    "assigned": "on_assigned",
    "mention": "on_mention",
    "comment": "on_comment",
    "resolved": "on_resolved",
    "status": "on_status",
    "sla_warning": "on_sla",
    "sla_breach": "on_sla",
}

# Push services reply with these when the browser has thrown the subscription
# away — uninstalled app, cleared site data, revoked permission.
DEAD_STATUSES = (404, 410)


# --------------------------------------------------------------------- keys
def generate_vapid_keys():
    """Print a fresh VAPID keypair. Run once, on the server, via bench execute.

    Deliberately not whitelisted: this mints a private key, and it belongs in
    site_config where the rest of the secrets live — never over HTTP.
    """
    try:
        from py_vapid import Vapid01 as Vapid
    except ImportError:
        print("pywebpush is not installed. Run:  bench pip install pywebpush")
        return
    import base64
    from cryptography.hazmat.primitives import serialization

    v = Vapid()
    v.generate_keys()

    def b64(raw):
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    private = b64(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
    public = b64(v.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint))
    print("\nAdd these to site_config.json:\n")
    print(json.dumps({
        "vapid_private_key": private,
        "vapid_public_key": public,
        "vapid_subject": "mailto:info@justyol.com",
    }, indent=2))
    print("\nThen: bench restart\n")


def _conf(key, default=None):
    return (frappe.conf or {}).get(key, default)


def is_configured():
    return bool(_conf("vapid_private_key") and _conf("vapid_public_key"))


@frappe.whitelist()
def public_key():
    """What the browser needs to create a subscription for this site."""
    gate_read()
    return {"key": _conf("vapid_public_key") or "", "enabled": is_configured()}


# ------------------------------------------------------------- subscriptions
def _device_label(user_agent):
    """A phrase a person can recognise among their own devices."""
    ua = user_agent or ""
    device = ("iPhone" if "iPhone" in ua else
              "iPad" if "iPad" in ua else
              "Android" if "Android" in ua else
              "Mac" if "Macintosh" in ua else
              "Windows" if "Windows" in ua else "Device")
    browser = ("Edge" if "Edg/" in ua else
               "Chrome" if "Chrome" in ua else
               "Firefox" if "Firefox" in ua else
               "Safari" if "Safari" in ua else "")
    return f"{device} · {browser}".strip(" ·") or "Device"


@frappe.whitelist()
def subscribe(subscription):
    """Store (or refresh) this browser's push subscription for the caller.

    Keyed on the endpoint, which the browser guarantees is unique per device
    per site — so re-subscribing after a permission re-grant updates the row
    instead of piling up duplicates that would each deliver the same buzz.
    """
    gate_read()
    if not is_configured():
        frappe.throw(_("Push notifications are not set up on this site yet."))

    data = subscription
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            frappe.throw(_("Malformed subscription."))
    if not isinstance(data, dict):
        frappe.throw(_("Malformed subscription."))

    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()
    if not (endpoint.startswith("https://") and p256dh and auth):
        frappe.throw(_("Malformed subscription."))

    user = frappe.session.user
    label = _device_label(frappe.get_request_header("User-Agent"))

    existing = frappe.db.get_value("Hub Push Subscription",
                                   {"endpoint": endpoint}, "name")
    if existing:
        doc = frappe.get_doc("Hub Push Subscription", existing)
        # An endpoint can be reissued to a different person on a shared
        # device; the row follows whoever subscribed last.
        doc.for_user = user
    else:
        doc = frappe.new_doc("Hub Push Subscription")
        doc.endpoint = endpoint
        doc.for_user = user
    doc.p256dh = p256dh
    doc.auth_secret = auth
    doc.device_label = label
    doc.last_seen = now_datetime()
    doc.failures = 0
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "device": label}


@frappe.whitelist()
def unsubscribe(endpoint=None):
    """Forget this device (or, with no endpoint, all of the caller's)."""
    gate_read()
    filters = {"for_user": frappe.session.user}
    if endpoint:
        filters["endpoint"] = endpoint
    names = frappe.get_all("Hub Push Subscription", filters=filters, pluck="name")
    for name in names:
        frappe.delete_doc("Hub Push Subscription", name, ignore_permissions=True,
                          force=True)
    frappe.db.commit()
    return {"removed": len(names)}


@frappe.whitelist()
def my_devices():
    """The caller's registered devices — so they can see and revoke them."""
    gate_read()
    return frappe.get_all(
        "Hub Push Subscription",
        filters={"for_user": frappe.session.user},
        fields=["name", "endpoint", "device_label", "last_seen"],
        order_by="last_seen desc")


# -------------------------------------------------------------- preferences
PREF_FIELDS = ["on_assigned", "on_mention", "on_comment", "on_resolved",
               "on_status", "on_sla"]


def _pref_doc(user):
    """The user's preference row, created on first read with the defaults."""
    name = frappe.db.get_value("Hub Push Preference", {"for_user": user}, "name")
    if name:
        return frappe.get_cached_doc("Hub Push Preference", name)
    doc = frappe.new_doc("Hub Push Preference")
    doc.for_user = user
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


@frappe.whitelist()
def get_preferences():
    gate_read()
    doc = _pref_doc(frappe.session.user)
    out = {f: int(doc.get(f) or 0) for f in PREF_FIELDS}
    out["quiet_from"] = str(doc.quiet_from or "")
    out["quiet_to"] = str(doc.quiet_to or "")
    return out


@frappe.whitelist()
def save_preferences(**kwargs):
    gate_read()
    doc = _pref_doc(frappe.session.user)
    for f in PREF_FIELDS:
        if f in kwargs:
            doc.set(f, 1 if kwargs[f] in (1, "1", True, "true") else 0)
    for f in ("quiet_from", "quiet_to"):
        if f in kwargs:
            doc.set(f, kwargs[f] or None)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return get_preferences()


def _as_time(value):
    if not value:
        return None
    if isinstance(value, dtime):
        return value
    m = re.match(r"^(\d{1,2}):(\d{2})", str(value))
    return dtime(int(m.group(1)) % 24, int(m.group(2))) if m else None


def _in_quiet_hours(doc, when=None):
    """Quiet hours silence the phone only — the bell and email still fire.

    Handles the overnight case (22:00 → 07:00) as one window rather than two,
    which is how anyone actually setting it means it.
    """
    start, end = _as_time(doc.quiet_from), _as_time(doc.quiet_to)
    if not (start and end) or start == end:
        return False
    now = (when or now_datetime()).time()
    if start < end:
        return start <= now < end
    return now >= start or now < end


def wants(user, ntype):
    """Does this user want their phone buzzed for this event, right now?"""
    try:
        doc = _pref_doc(user)
    except Exception:
        return True  # preferences not migrated yet — don't swallow alerts
    field = NTYPE_PREF.get(ntype)
    if field and not int(doc.get(field) or 0):
        return False
    return not _in_quiet_hours(doc)


# --------------------------------------------------------------- delivery
def _drop(name):
    try:
        frappe.delete_doc("Hub Push Subscription", name,
                          ignore_permissions=True, force=True)
    except Exception:
        pass


def send(user, title, body, url=None, ntype=None, tag=None):
    """Buzz every device this user has registered. Never raises.

    Returns the number of devices reached, which is what makes this testable
    from bench without a phone in hand.
    """
    if not is_configured() or not user or user in ("Guest", "Administrator"):
        return 0
    if ntype and not wants(user, ntype):
        return 0
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        frappe.log_error(message="pywebpush is not installed "
                                 "(bench pip install pywebpush)",
                         title="task_hub: push unavailable")
        return 0

    rows = frappe.get_all(
        "Hub Push Subscription", filters={"for_user": user},
        fields=["name", "endpoint", "p256dh", "auth_secret"])
    if not rows:
        return 0

    payload = json.dumps({
        "title": title,
        "body": (body or "")[:300],
        "url": url or "/taskhub",
        "tag": tag or ntype or "task-hub",
    })
    claims = {"sub": _conf("vapid_subject") or "mailto:info@justyol.com"}
    sent = 0
    for row in rows:
        try:
            webpush(
                subscription_info={
                    "endpoint": row.endpoint,
                    "keys": {"p256dh": row.p256dh, "auth": row.auth_secret},
                },
                data=payload,
                vapid_private_key=_conf("vapid_private_key"),
                vapid_claims=dict(claims),
                ttl=86400,
            )
            sent += 1
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in DEAD_STATUSES:
                # The browser discarded this subscription; keeping the row
                # would mean retrying a dead endpoint on every notification.
                _drop(row.name)
            else:
                frappe.db.set_value("Hub Push Subscription", row.name, "failures",
                                    (frappe.db.get_value(
                                        "Hub Push Subscription", row.name,
                                        "failures") or 0) + 1,
                                    update_modified=False)
        except Exception:
            frappe.log_error(message=frappe.get_traceback(),
                             title="task_hub: push send failed")
    if sent:
        frappe.db.commit()
    return sent


@frappe.whitelist()
def send_test():
    """Buzz the caller's own devices — the only way to prove the chain works
    end to end without waiting for a real ticket event."""
    gate_read()
    n = send(frappe.session.user, "Task Hub",
             _("Test notification — your phone is set up."),
             url="/taskhub", tag="test")
    return {"sent": n}


def purge_dead_subscriptions():
    """Weekly: devices that have failed repeatedly are not coming back."""
    frappe.db.sql("DELETE FROM `tabHub Push Subscription` WHERE failures >= 10")
    frappe.db.commit()
