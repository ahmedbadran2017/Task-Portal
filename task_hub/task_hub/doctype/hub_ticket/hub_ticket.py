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

# Priority → SLA budget in hours. Urgent must move fast; Low is best-effort.
SLA_HOURS = {
    "Urgent": 4,
    "High": 24,
    "Medium": 72,
    "Low": 168,  # one week
}

# Statuses that mean the ticket is done — freeze the SLA clock here.
CLOSED_STATES = {"Resolved", "Closed", "Cancelled"}


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
        hours = SLA_HOURS.get(self.priority or "Medium", 72)
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
