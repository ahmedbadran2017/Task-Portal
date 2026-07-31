import frappe
from frappe import _
from frappe.model.document import Document


class HubGoal(Document):
    def validate(self):
        if self.period_start and self.period_end and str(self.period_start) > str(self.period_end):
            frappe.throw(_("The period ends before it starts."))
        if (self.target_value or 0) <= 0:
            frappe.throw(_("The target must be above zero."))
