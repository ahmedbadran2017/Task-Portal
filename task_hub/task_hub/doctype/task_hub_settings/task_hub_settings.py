import frappe  # noqa: F401
from frappe.model.document import Document


class TaskHubSettings(Document):
    pass


def get_sla_hours():
    """Priority → SLA hours, from settings with hard fallbacks. Used by the
    Hub Ticket controller and the breach-refresh job."""
    defaults = {"Urgent": 4, "High": 24, "Medium": 72, "Low": 168}
    try:
        s = frappe.get_cached_doc("Task Hub Settings")
    except Exception:
        return defaults
    return {
        "Urgent": int(s.sla_urgent_hours or 0) or defaults["Urgent"],
        "High": int(s.sla_high_hours or 0) or defaults["High"],
        "Medium": int(s.sla_medium_hours or 0) or defaults["Medium"],
        "Low": int(s.sla_low_hours or 0) or defaults["Low"],
    }
