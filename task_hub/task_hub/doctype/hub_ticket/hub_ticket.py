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


# Portal → department label. Kept here so the whole app agrees on the mapping.
PORTAL_DEPARTMENT = {
    "Supplier": "Supplier Operations",
    "Accounting": "Finance & Accounting",
    "Logistics": "Logistics & Fulfilment",
    "Purchasing": "Procurement",
    "Other": "General",
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
            if self.status in CLOSED_STATES and not self.resolved_on:
                self.resolved_on = now_datetime()
            if self.status not in CLOSED_STATES:
                # Re-opened — clear the resolution stamp.
                self.resolved_on = None

        # Assignment transitions
        if (before.assigned_to or "") != (self.assigned_to or ""):
            if self.assigned_to:
                self._log("Assigned", _("Assigned to {0}").format(self.assigned_to))
                self._notify_assignee()
            else:
                self._log("Unassigned", _("Assignment cleared"))

        # Priority changes re-price the SLA only while the ticket is still open.
        if before.priority != self.priority and self.status not in CLOSED_STATES:
            self._set_sla_deadline()
            self._log("Priority changed", _("{0} → {1}").format(before.priority, self.priority))

        self._refresh_breach_flag()

    # -------------------------------------------------------------- helpers
    def _sync_department(self):
        if not self.department:
            self.department = PORTAL_DEPARTMENT.get(self.source_portal or "Other", "General")

    def _set_sla_deadline(self):
        hours = _sla_hours().get(self.priority or "Medium", 72)
        base = get_datetime(self.creation) if self.creation else now_datetime()
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
        """Email the new assignee, if notifications are on and it isn't a
        self-assignment."""
        try:
            s = frappe.get_cached_doc("Task Hub Settings")
            if not int(s.notify_on_assignment or 0):
                return
        except Exception:
            pass  # settings not migrated yet — default to notifying
        if self.assigned_to == frappe.session.user:
            return
        try:
            frappe.sendmail(
                recipients=[self.assigned_to],
                subject=_("[Task Hub] {0} assigned to you").format(self.name),
                message=(
                    f"<p><b>{self.title}</b> ({self.priority} · "
                    f"{self.source_portal}) was assigned to you by "
                    f"{frappe.session.user}.</p>"
                    f'<p><a href="/taskhub/tickets">Open the Task Hub →</a></p>'
                ),
            )
        except Exception:
            frappe.log_error(message=frappe.get_traceback(),
                             title="task_hub: assignment email failed")


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
