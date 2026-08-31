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


def hub_url(path="/taskhub"):
    """Absolute link into the SPA — see task_hub.notify.hub_url for why these
    can't be relative once they leave for a mail client."""
    from task_hub.notify import hub_url as _u
    return _u(path)


def _link(href, label):
    return f'<a href="{href}">{label}</a>'


def _ticket_link(name):
    from task_hub.notify import deep_link
    return f'<a href="{deep_link(name)}">{name}</a>'


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
        budget -= _detect_stuck_orders(s, budget)
    if budget > 0 and cint(s.auto_item_content):
        _detect_items_missing_content(s, budget)


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


def _content_workspace():
    """The workspace whose department is the content team (Ecommerce - ML),
    found dynamically so renaming/re-owning it in Settings just works."""
    ws = frappe.db.get_value("Hub Workspace", {"department": "Ecommerce - ML"})
    return ws  # None → ticket lands in the default workspace


def _detect_items_missing_content(s, budget):
    """New Items with no image or no description → one Task each for the
    content team. Fires once per item, ever — resolving the ticket without
    fixing the item must not resurrect it daily."""
    days = cint(s.item_content_days) or 7
    since = add_days(nowdate(), -days)
    rows = frappe.db.sql(
        """SELECT name, item_name, item_code, image, description
           FROM `tabItem`
           WHERE disabled = 0 AND creation >= %s
             AND (image IS NULL OR image = ''
                  OR description IS NULL OR description = ''
                  OR CHAR_LENGTH(description) < 20)
           ORDER BY creation DESC
           LIMIT %s""",
        # Only `budget` tickets can be created per run; scanning far beyond
        # that just loads a bulk import into memory. Head-room covers rows
        # skipped by the dedupe check below.
        (since, budget * 20), as_dict=True,
    )
    workspace = _content_workspace()
    created = 0
    for r in rows:
        if created >= budget:
            break
        # once-ever dedupe: any auto ticket for this Item, open or closed
        if frappe.db.exists("Hub Ticket", {
                "linked_doctype": "Item", "linked_name": r.name,
                "auto_generated": 1}):
            continue
        missing = []
        if not r.image:
            missing.append("image")
        if not r.description or len(r.description or "") < 20:
            missing.append("description")
        _make_auto_ticket(
            title=f"Add content: {r.item_name or r.item_code}",
            description=(
                f"Item <b>{r.item_code}</b> is missing: "
                f"<b>{', '.join(missing)}</b>. Complete the listing content."
            ),
            ticket_type="Task",
            priority="Medium",
            source_portal="Website",
            workspace=workspace,
            linked_doctype="Item",
            linked_name=r.name,
            linked_label=r.item_code or r.name,
            linked_url=f"/app/item/{r.name}",
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
        limit_page_length=500,
    ):
        deadline = get_datetime(t.sla_deadline)
        total = (deadline - get_datetime(t.creation)).total_seconds()
        left = (deadline - now).total_seconds()
        if total <= 0 or left <= 0 or left > total * 0.25:
            continue
        hours_left = max(1, int(left // 3600))
        from task_hub.notify import push
        try:
            push(
                t.assigned_to, t.name, "sla_warning",
                f"SLA warning: ~{hours_left}h left on {t.name} — {t.title}",
                email_subject=f"[Task Hub] {t.name} nears its SLA ({hours_left}h left)",
                email_html=(f"<p><b>{frappe.utils.escape_html(t.title)}</b> ({t.priority}) breaches its SLA "
                            f"in about <b>{hours_left}h</b>.</p>"),
            )
        except Exception:
            frappe.log_error(title=f"Hub SLA warning {t.name}",
                             message=frappe.get_traceback()[:2000])
            continue
        frappe.db.set_value("Hub Ticket", t.name, "sla_warning_sent", 1,
                            update_modified=False)
        # Commit per ticket: the mail has already left, so a later failure
        # must not roll the flag back and re-send the same warning next hour.
        frappe.db.commit()

    # Escalations — breached and not yet escalated.
    breached = frappe.get_all(
        "Hub Ticket",
        filters={
            "status": ["in", OPEN_STATES],
            "sla_breached": 1,
            "sla_breach_notified": 0,
        },
        fields=["name", "title", "priority", "source_portal", "assigned_to"],
        limit_page_length=200,
    )
    if breached:
        from task_hub.notify import push
        for t in breached:
            if t.assigned_to:
                push(t.assigned_to, t.name, "sla_breach",
                     f"SLA breached: {t.name} — {t.title}")
        managers = _manager_emails(s)
        items = "".join(
            f"<li><b>{t.name}</b> · {frappe.utils.escape_html(t.title)} ({t.source_portal}, {t.priority}, "
            f"assignee: {t.assigned_to or 'unassigned'})</li>"
            for t in breached
        )
        _sendmail(
            managers,
            f"[Task Hub] {len(breached)} ticket(s) breached SLA",
            f"<p>These tickets are past their SLA deadline:</p><ul>{items}</ul>"
            f'<p><a href="{hub_url("/taskhub/tickets?breached=1")}">'
            f"Open the breach list →</a></p>",
        )
        for t in breached:
            frappe.db.set_value("Hub Ticket", t.name, "sla_breach_notified", 1,
                                update_modified=False)
    frappe.db.commit()


# ════════════════════════════════════════════════════════════ monthly scorecard
def send_monthly_scorecard():
    """Monthly: department + top-performer scorecard to the managers. Reuses
    the weekly_digest toggle — one switch controls both periodic reports."""
    s = _settings()
    if not s or not cint(s.weekly_digest):
        return
    from task_hub.api.scorecards import department_scorecard, employee_scorecard

    # The scorecards are manager-gated; run them as Administrator but ALWAYS
    # restore, or every scheduler job queued behind this one in the same
    # worker inherits Administrator rights.
    previous_user = frappe.session.user
    try:
        frappe.set_user("Administrator")
        depts = department_scorecard(days=30)["departments"]
        people = employee_scorecard(days=30)["employees"][:10]
    finally:
        frappe.set_user(previous_user)
    if not depts and not people:
        return

    drows = "".join(
        f"<tr><td>{d['department']}</td><td>{d['members']}</td><td>{d['open']}</td>"
        f"<td>{d['breached']}</td><td>{d['resolved']}</td>"
        f"<td>{d['avg_resolution_hours'] if d['avg_resolution_hours'] is not None else '—'}</td>"
        f"<td>{str(d['sla_compliance_pct']) + '%' if d['sla_compliance_pct'] is not None else '—'}</td></tr>"
        for d in depts
    )
    prows = "".join(
        f"<tr><td>{p['full_name']}</td><td>{p['resolved']}</td><td>{p['open']}</td>"
        f"<td>{p['avg_resolution_hours'] if p['avg_resolution_hours'] is not None else '—'}</td>"
        f"<td>{str(p['sla_compliance_pct']) + '%' if p['sla_compliance_pct'] is not None else '—'}</td></tr>"
        for p in people
    )
    teams_link = hub_url("/taskhub/teams")
    _sendmail(
        _manager_emails(s),
        "[Task Hub] Monthly performance scorecard",
        f"""<p>Task Hub — last 30 days.</p>
        <h4>Departments</h4>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>Department</th><th>People</th><th>Open</th><th>Breached</th>
              <th>Resolved</th><th>Avg hours</th><th>SLA on-time</th></tr>
          {drows}
        </table>
        <h4>Top resolvers</h4>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>Person</th><th>Resolved</th><th>Open now</th>
              <th>Avg hours</th><th>SLA on-time</th></tr>
          {prows}
        </table>
        <p><a href="{teams_link}">Open the Teams view →</a></p>""",
    )


# ════════════════════════════════════════════════════════════ weekly digest
def send_weekly_digest():
    s = _settings()
    if not s or not cint(s.weekly_digest):
        return
    week_ago = add_days(nowdate(), -7)

    def count(filters):
        return frappe.db.count("Hub Ticket", filters=filters)

    portals = ["Supplier", "Accounting", "Logistics", "Purchasing", "JoyAgent",
               "Website", "Mobile App", "Other"]
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

    # Optional AI paragraph on top of the raw table — best-effort, the
    # digest goes out either way.
    summary_html = ""
    try:
        from task_hub.api.ai import is_enabled, call_anthropic
        if is_enabled():
            summary = call_anthropic(
                "You summarize a weekly ops digest for managers at Justyol. "
                "Given an HTML table of ticket stats per portal (columns: "
                "portal, new, resolved, open now, SLA-breached), write 2-3 "
                "short bullet points in Arabic: the headline, the biggest "
                "risk, and one suggested focus. Plain text bullets only.",
                rows, max_tokens=300)
            summary_html = ("<p><b>ملخص الأسبوع:</b><br>"
                            + summary.replace("\n", "<br>") + "</p>")
    except Exception:
        pass

    _sendmail(
        _manager_emails(s),
        "[Task Hub] Weekly digest",
        summary_html + """<p>Task Hub — last 7 days:</p>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>Portal</th><th>New</th><th>Resolved</th>
              <th>Open now</th><th>Breached</th></tr>""" + rows + """
        </table>
        <p>""" + _link(hub_url("/taskhub"), "Open the Task Hub →") + """</p>""",
    )
