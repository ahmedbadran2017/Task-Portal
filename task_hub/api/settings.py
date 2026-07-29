"""Task Hub settings — read for everyone, write for managers."""
import frappe
from frappe import _

from task_hub.api.utils import gate_read, gate_manager

FIELDS = [
    "sla_urgent_hours", "sla_high_hours", "sla_medium_hours", "sla_low_hours",
    "default_ticket_type", "default_priority", "auto_refresh_seconds",
    "auto_overdue_invoices", "overdue_invoice_days",
    "auto_stuck_orders", "stuck_order_days", "max_auto_tickets_per_run",
    "notify_on_assignment", "notify_sla", "weekly_digest", "digest_recipients",
    "assignee_scope",
]

# Check fields arrive as 0/1 and may legitimately be 0 — updated even when falsy.
CHECK_FIELDS = {
    "auto_overdue_invoices", "auto_stuck_orders",
    "notify_on_assignment", "notify_sla", "weekly_digest",
}

BOUNDS = {  # sane clamps so a typo can't produce a 0-hour or 10-year SLA
    "sla_urgent_hours": (1, 720),
    "sla_high_hours": (1, 2160),
    "sla_medium_hours": (1, 4320),
    "sla_low_hours": (1, 8760),
    "auto_refresh_seconds": (0, 3600),
    "overdue_invoice_days": (1, 90),
    "stuck_order_days": (1, 90),
    "max_auto_tickets_per_run": (1, 200),
}


@frappe.whitelist()
def get_settings():
    gate_read()
    s = frappe.get_cached_doc("Task Hub Settings")
    return {f: s.get(f) for f in FIELDS}


@frappe.whitelist()
def update_settings(**kwargs):
    gate_manager()
    s = frappe.get_doc("Task Hub Settings")
    for f in FIELDS:
        if f not in kwargs:
            continue
        val = kwargs[f]
        if f in CHECK_FIELDS:
            s.set(f, 1 if val in (1, "1", True, "true") else 0)
            continue
        if f == "digest_recipients":
            s.set(f, (val or "").strip()[:1000])
            continue
        if val in (None, ""):
            continue
        if f in BOUNDS:
            try:
                val = int(val)
            except (TypeError, ValueError):
                frappe.throw(_("{0} must be a number.").format(f))
            lo, hi = BOUNDS[f]
            val = max(lo, min(hi, val))
        s.set(f, val)
    s.save(ignore_permissions=True)
    frappe.clear_document_cache("Task Hub Settings", "Task Hub Settings")
    frappe.db.commit()
    return {f: s.get(f) for f in FIELDS}
