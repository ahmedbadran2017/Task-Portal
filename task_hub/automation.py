"""
Phase 3 — automation & notifications.

Everything here runs from the scheduler (see hooks.py) and is gated by
Task Hub Settings, with the auto-ticket rules OFF by default so enabling
them on production is a deliberate choice.

Jobs:
  run_auto_rules        (daily)  — detectors create Hub Tickets from portal data
  notify_sla_risks      (hourly) — warn assignees near deadline, escalate breaches
  send_weekly_digest    (weekly) — per-portal summary to managers
"""
import frappe
from frappe.utils import add_days, nowdate, now_datetime, get_datetime, cint

OPEN_STATES = ("Open", "In Progress", "In Review")


def _settings():
    try:
        return frappe.get_cached_doc("Task Hub Settings")
    except Exception:
        return None


def _manager_emails(settings=None):
    """Explicit digest recipients, else every enabled Task Hub manager/admin."""
    s = settings or _settings()
    raw = (s.digest_recipients or "") if s else ""
    explicit = [e.strip() for e in raw.replace("\n", ",").split(",") if e.strip()]
    if explicit:
        return explicit
    rows = frappe.get_all(
        "Has Role",
        filters={"role": ["in", ("Task Hub Admin", "Task Hub Manager")], "parenttype": "User"},
        fields=["parent"],
    )
    users = {r.parent for r in rows}
    return [
        u for u in users
        if u not in ("Administrator", "Guest")
        and frappe.db.get_value("User", u, "enabled")
    ]


def _sendmail(recipients, subject, message):
    if not recipients:
        return
    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
    except Exception:
        frappe.log_error(message=frappe.get_traceback(),
                         title="task_hub: sendmail failed")


def _ticket_link(name):
    return f'<a href="/taskhub/tickets">{name}</a>'


# ════════════════════════════════════════════════════════════ auto-tickets
def run_auto_rules():
    """Daily: run every enabled detector, capped per run."""
    s = _settings()
    if not s:
        return
    budget = cint(s.max_auto_tickets_per_run) or 20
    if cint(s.auto_overdue_invoices):
        budget -= _detect_overdue_invoices(s, budget)
    if budget > 0 and cint(s.auto_stuck_orders):
        _detect_stuck_orders(s, budget)


def _open_auto_ticket_exists(linked_doctype, linked_name):
    return frappe.db.exists("Hub Ticket", {
        "linked_doctype": linked_doctype,
        "linked_name": linked_name,
        "auto_generated": 1,
        "status": ["in", OPEN_STATES],
    })


def _make_auto_ticket(**kw):
    doc = frappe.new_doc("Hub Ticket")
    doc.update(kw)
    doc.auto_generated = 1
    doc.reported_by = "Administrator"
    doc.insert(ignore_permissions=True)
    return doc


def _detect_overdue_invoices(s, budget):
    """Submitted Sales Invoices with outstanding money past due_date + N days."""
    cutoff = add_days(nowdate(), -(cint(s.overdue_invoice_days) or 3))
    rows = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "outstanding_amount": [">", 0],
            "due_date": ["<", cutoff],
        },
        fields=["name", "customer", "outstanding_amount", "due_date", "currency"],
        order_by="due_date asc",
        limit_page_length=budget * 3,  # headroom for already-ticketed rows
    )
    created = 0
    for r in rows:
        if created >= budget:
            break
        if _open_auto_ticket_exists("Sales Invoice", r.name):
            continue
        _make_auto_ticket(
            title=f"Overdue invoice {r.name} — {r.customer}",
            description=(
                f"Invoice <b>{r.name}</b> for <b>{r.customer}</b> has "
                f"<b>{r.outstanding_amount:,.0f} {r.currency}</b> outstanding, "
                f"due since {r.due_date}."
            ),
            ticket_type="Problem",
            priority="High",
            source_portal="Accounting",
            linked_doctype="Sales Invoice",
            linked_name=r.name,
            linked_label=r.name,
            linked_url=f"/app/sales-invoice/{r.name}",
        )
        created += 1
    if created:
        frappe.db.commit()
    return created


def _detect_stuck_orders(s, budget):
    """Submitted Sales Orders still undelivered N days after their date."""
    cutoff = add_days(nowdate(), -(cint(s.stuck_order_days) or 3))
    rows = frappe.get_all(
        "Sales Order",
        filters={
            "docstatus": 1,
            "status": ["in", ("To Deliver", "To Deliver and Bill")],
            "transaction_date": ["<", cutoff],
        },
        fields=["name", "customer", "transaction_date", "delivery_date"],
        order_by="transaction_date asc",
        limit_page_length=budget * 3,
    )
    created = 0
    for r in rows:
        if created >= budget:
            break
        if _open_auto_ticket_exists("Sales Order", r.name):
            continue
        _make_auto_ticket(
            title=f"Order {r.name} not delivered — {r.customer}",
            description=(
                f"Sales Order <b>{r.name}</b> ({r.customer}, dated "
                f"{r.transaction_date}) is still undelivered."
            ),
            ticket_type="Problem",
            priority="High",
            source_portal="Logistics",
            linked_doctype="Sales Order",
            linked_name=r.name,
            linked_label=r.name,
            linked_url=f"/app/sales-order/{r.name}",
        )
        created += 1
    if created:
        frappe.db.commit()
    return created


# ════════════════════════════════════════════════════════════ SLA notifications
def notify_sla_risks():
    """Hourly: warn assignees when <25% of the SLA budget remains; escalate
    breaches to the managers once."""
    s = _settings()
    if not s or not cint(s.notify_sla):
        return
    now = now_datetime()

    # Warnings — assigned, open, unwarned, inside the final quarter of budget.
    for t in frappe.get_all(
        "Hub Ticket",
        filters={
            "status": ["in", OPEN_STATES],
            "sla_warning_sent": 0,
            "sla_deadline": ["is", "set"],
            "assigned_to": ["is", "set"],
        },
        fields=["name", "title", "priority", "assigned_to", "sla_deadline", "creation"],
    ):
        deadline = get_datetime(t.sla_deadline)
        total = (deadline - get_datetime(t.creation)).total_seconds()
        left = (deadline - now).total_seconds()
        if total <= 0 or left <= 0 or left > total * 0.25:
            continue
        hours_left = max(1, int(left // 3600))
        _sendmail(
            [t.assigned_to],
            f"[Task Hub] {t.name} nears its SLA ({hours_left}h left)",
            f"<p><b>{t.title}</b> ({t.priority}) breaches its SLA in about "
            f"<b>{hours_left}h</b>. {_ticket_link(t.name)}</p>",
        )
        frappe.db.set_value("Hub Ticket", t.name, "sla_warning_sent", 1,
                            update_modified=False)

    # Escalations — breached and not yet escalated.
    breached = frappe.get_all(
        "Hub Ticket",
        filters={
            "status": ["in", OPEN_STATES],
            "sla_breached": 1,
            "sla_breach_notified": 0,
        },
        fields=["name", "title", "priority", "source_portal", "assigned_to"],
    )
    if breached:
        managers = _manager_emails(s)
        items = "".join(
            f"<li><b>{t.name}</b> · {t.title} ({t.source_portal}, {t.priority}, "
            f"assignee: {t.assigned_to or 'unassigned'})</li>"
            for t in breached
        )
        _sendmail(
            managers,
            f"[Task Hub] {len(breached)} ticket(s) breached SLA",
            f"<p>These tickets are past their SLA deadline:</p><ul>{items}</ul>"
            f'<p><a href="/taskhub/tickets?breached=1">Open the breach list →</a></p>',
        )
        for t in breached:
            frappe.db.set_value("Hub Ticket", t.name, "sla_breach_notified", 1,
                                update_modified=False)
    frappe.db.commit()


# ════════════════════════════════════════════════════════════ weekly digest
def send_weekly_digest():
    s = _settings()
    if not s or not cint(s.weekly_digest):
        return
    week_ago = add_days(nowdate(), -7)

    def count(filters):
        return frappe.db.count("Hub Ticket", filters=filters)

    portals = ["Supplier", "Accounting", "Logistics", "Purchasing", "Other"]
    rows = ""
    for p in portals:
        opened = count({"source_portal": p, "creation": [">=", week_ago]})
        resolved = count({"source_portal": p, "resolved_on": [">=", week_ago]})
        open_now = count({"source_portal": p, "status": ["in", OPEN_STATES]})
        breached = count({"source_portal": p, "status": ["in", OPEN_STATES], "sla_breached": 1})
        if not any((opened, resolved, open_now, breached)):
            continue
        rows += (f"<tr><td>{p}</td><td>{opened}</td><td>{resolved}</td>"
                 f"<td>{open_now}</td><td>{breached}</td></tr>")
    if not rows:
        return

    _sendmail(
        _manager_emails(s),
        "[Task Hub] Weekly digest",
        """<p>Task Hub — last 7 days:</p>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>Portal</th><th>New</th><th>Resolved</th>
              <th>Open now</th><th>Breached</th></tr>""" + rows + """
        </table>
        <p><a href="/taskhub">Open the Task Hub →</a></p>""",
    )
