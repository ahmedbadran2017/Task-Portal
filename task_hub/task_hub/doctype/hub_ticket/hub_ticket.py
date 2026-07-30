"""
Hub Ticket — one task / problem / request raised from any Justyol portal.

Lifecycle is enforced here (not via doc_events) because this app owns the
DocType. The controller:
  * stamps reporter + SLA deadline on insert,
  * derives the department from the source portal,
  * appends an immutable activity row on every status/assignment change,
  * marks resolution + SLA breach automatically.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_to_date


# Portal → default ERPNext Department, used only when the reporter has no
# Employee record (external systems, Administrator, automations). Names must
# match real `tabDepartment` rows — guarded by an exists() check before use.
PORTAL_DEPARTMENT = {
    "Supplier": "Operations - JM",
    "Accounting": "Accounts - JM",
    "Logistics": "Logistics - JM",
    "Purchasing": "Purchase - JM",
    "JoyAgent": "Customer Service - JM",
    "Website": "Ecommerce - ML",
    "Mobile App": "Ecommerce - ML",
    "Other": None,
}

# Statuses that mean the ticket is done — freeze the SLA clock here.
CLOSED_STATES = {"Resolved", "Closed", "Cancelled"}


def _sla_hours():
    from task_hub.task_hub.doctype.task_hub_settings.task_hub_settings import get_sla_hours
    return get_sla_hours()


class HubTicket(Document):
    # -------------------------------------------------------------- insert
    def before_insert(self):
        if not self.reported_by:
            self.reported_by = frappe.session.user
        if not self.status:
            self.status = "Open"
        if not self.priority:
            self.priority = "Medium"
        self._sync_department()
        self._set_sla_deadline()
        self.append("activity", {
            "activity_on": now_datetime(),
            "actor": frappe.session.user,
            "action": "Created",
            "detail": _("Ticket created ({0} · {1})").format(
                self.ticket_type or "Task", self.priority),
        })

    def after_insert(self):
        # A ticket born with an assignee must notify them too — before_save
        # only catches later re-assignments.
        if self.assigned_to:
            self._notify_assignee()

    # -------------------------------------------------------------- update
    def before_save(self):
        if self.is_new():
            return
        before = self.get_doc_before_save()
        if not before:
            return

        self._sync_department()

        # Status transitions
        if before.status != self.status:
            self._log("Status changed", _("{0} → {1}").format(before.status, self.status))
            self._notify_watchers(
                "status", _("{0}: {1} → {2}").format(self.name, before.status, self.status))
            if self.status in CLOSED_STATES and not self.resolved_on:
                self.resolved_on = now_datetime()
                self._notify_resolved()
            if self.status not in CLOSED_STATES:
                # Re-opened — clear the resolution stamp AND the notification
                # bookkeeping, so a revived ticket can warn/escalate again.
                self.resolved_on = None
                if before.status in CLOSED_STATES:
                    self.sla_warning_sent = 0
                    self.sla_breach_notified = 0

        # Assignment transitions
        if (before.assigned_to or "") != (self.assigned_to or ""):
            if self.assigned_to:
                self._log("Assigned", _("Assigned to {0}").format(self.assigned_to))
                self._notify_assignee()
            else:
                self._log("Unassigned", _("Assignment cleared"))

        # Priority changes re-price the SLA only while the ticket is still open.
        if before.priority != self.priority and self.status not in CLOSED_STATES:
            self._set_sla_deadline(from_now=True)
            # Deadline moved — allow a fresh warning for the new window.
            self.sla_warning_sent = 0
            self._log("Priority changed", _("{0} → {1}").format(before.priority, self.priority))

        self._refresh_breach_flag()

    # -------------------------------------------------------------- helpers
    def _sync_department(self):
        """Stamp the real ERPNext Department: an explicitly-set valid value
        wins, else the reporter's Employee department, else the portal's
        default. Invalid names are dropped rather than failing the save."""
        if self.department and not frappe.db.exists("Department", self.department):
            self.department = None
        if self.department:
            return
        self.department = resolve_user_department(self.reported_by) or None
        if not self.department:
            fallback = PORTAL_DEPARTMENT.get(self.source_portal or "Other")
            if fallback and frappe.db.exists("Department", fallback):
                self.department = fallback

    def _set_sla_deadline(self, from_now=False):
        """On creation the clock starts at `creation`; a later re-price starts
        a fresh window from now — otherwise raising a 3-day-old ticket to
        Urgent (4h budget) marks it breached instantly."""
        hours = _sla_hours().get(self.priority or "Medium", 72)
        base = now_datetime() if from_now else (
            get_datetime(self.creation) if self.creation else now_datetime())
        self.sla_deadline = add_to_date(base, hours=hours)
        self._refresh_breach_flag()

    def _refresh_breach_flag(self):
        if self.status in CLOSED_STATES or not self.sla_deadline:
            self.sla_breached = 0
            return
        self.sla_breached = 1 if now_datetime() > get_datetime(self.sla_deadline) else 0

    def _log(self, action, detail):
        self.append("activity", {
            "activity_on": now_datetime(),
            "actor": frappe.session.user,
            "action": action,
            "detail": detail,
        })

    def _notify_assignee(self):
        """In-app always; email if the assignment toggle is on. Skips
        self-assignment."""
        from task_hub.notify import push

        if self.assigned_to == frappe.session.user:
            return
        email_on = True
        try:
            s = frappe.get_cached_doc("Task Hub Settings")
            email_on = bool(int(s.notify_on_assignment or 0))
        except Exception:
            pass  # settings not migrated yet — default to emailing
        push(
            self.assigned_to, self.name, "assigned",
            _("{0} assigned you: {1}").format(
                frappe.utils.get_fullname(frappe.session.user), self.title),
            email_subject=(_("[Task Hub] {0} assigned to you").format(self.name)
                           if email_on else None),
            email_html=(f"<p><b>{frappe.utils.escape_html(self.title)}</b> "
                        f"({self.priority} · {self.source_portal}) was assigned "
                        f"to you by "
                        f"{frappe.utils.get_fullname(frappe.session.user)}.</p>"),
        )

    def watcher_list(self):
        return [w.strip() for w in (self.watchers or "").split(",") if w.strip()]

    def _notify_watchers(self, ntype, message):
        """In-app only — watchers opted in to follow, not to be emailed."""
        from task_hub.notify import push
        for w in set(self.watcher_list()) - {frappe.session.user}:
            push(w, self.name, ntype, message)

    def _notify_resolved(self):
        """Tell the reporter their ticket was resolved (unless they did it)."""
        from task_hub.notify import push

        if not self.reported_by or self.reported_by == frappe.session.user:
            return
        push(
            self.reported_by, self.name, "resolved",
            _("Your ticket was resolved: {0}").format(self.title),
            email_subject=_("[Task Hub] {0} resolved").format(self.name),
            email_html=(f"<p>Your ticket <b>{frappe.utils.escape_html(self.title)}</b> "
                        f"was marked <b>{self.status}</b> by "
                        f"{frappe.utils.get_fullname(frappe.session.user)}.</p>"),
        )


def resolve_user_department(user):
    """The user's real department from their Employee record, or None."""
    if not user or user in ("Guest", "Administrator"):
        return None
    dept = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"},
                               "department")
    return dept if dept and frappe.db.exists("Department", dept) else None


def refresh_sla_breaches():
    """Hourly scheduler job: flag open tickets whose SLA deadline has passed.

    Without this, `sla_breached` only updates when a ticket happens to be
    saved — a ticket nobody touches would never show as breached.
    """
    frappe.db.sql(
        """
        UPDATE `tabHub Ticket`
        SET sla_breached = 1
        WHERE sla_breached = 0
          AND status IN ('Open', 'In Progress', 'In Review')
          AND sla_deadline IS NOT NULL
          AND sla_deadline < NOW()
        """
    )
    frappe.db.commit()
