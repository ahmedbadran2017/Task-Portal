import frappe
from frappe import _
from frappe.model.document import Document

GLOBAL_STATUSES = ["Open", "In Progress", "In Review", "Resolved", "Closed", "Cancelled"]

# Stage template for brand-new workspaces — simple 4-column flow.
DEFAULT_STAGES = [
    {"stage_name": "To Do", "maps_to": "Open", "color": "#3b82f6"},
    {"stage_name": "Doing", "maps_to": "In Progress", "color": "#a16207"},
    {"stage_name": "Review", "maps_to": "In Review", "color": "#7c3aed"},
    {"stage_name": "Done", "maps_to": "Resolved", "color": "#059669"},
]


class HubWorkspace(Document):
    def validate(self):
        if not self.stages:
            for s in DEFAULT_STAGES:
                self.append("stages", s)
        names = [s.stage_name.strip() for s in self.stages]
        if len(names) != len(set(names)):
            frappe.throw(_("Stage names must be unique within a workspace."))
        # At least one open-ish and one done-ish stage keeps flows coherent.
        maps = {s.maps_to for s in self.stages}
        if not maps & {"Open", "In Progress", "In Review"}:
            frappe.throw(_("Add at least one active stage (Open/In Progress/In Review)."))
        if not maps & {"Resolved", "Closed"}:
            frappe.throw(_("Add at least one finishing stage (Resolved/Closed)."))


def get_default_workspace():
    name = frappe.db.get_value("Hub Workspace", {"is_default": 1})
    return name


def workspace_members(name):
    """Department's active employees + explicit extras."""
    ws = frappe.get_cached_doc("Hub Workspace", name)
    members = set()
    if ws.department:
        for r in frappe.get_all(
            "Employee",
            filters={"status": "Active", "department": ws.department,
                     "user_id": ["is", "set"]},
            fields=["user_id"],
        ):
            members.add(r.user_id)
    for m in (ws.extra_members or "").replace("\n", ",").split(","):
        if m.strip():
            members.add(m.strip())
    return sorted(members)


def stage_for_status(ws_doc, status):
    """First stage of the workspace that maps to `status` (fallback: first)."""
    for s in ws_doc.stages:
        if s.maps_to == status:
            return s.stage_name
    return ws_doc.stages[0].stage_name if ws_doc.stages else None


def ensure_default_workspace():
    """Idempotent: the system ships with 'Technical Support' as the default
    workspace whose stages mirror the six global statuses 1:1."""
    if frappe.db.exists("Hub Workspace", {"is_default": 1}):
        return frappe.db.get_value("Hub Workspace", {"is_default": 1})
    doc = frappe.new_doc("Hub Workspace")
    doc.workspace_name = "Technical Support"
    doc.icon = "🛠️"
    doc.color = "#d45d3e"
    doc.use_sla = 1
    doc.is_default = 1
    colors = {"Open": "#3b82f6", "In Progress": "#a16207", "In Review": "#7c3aed",
              "Resolved": "#059669", "Closed": "#475569", "Cancelled": "#9f1239"}
    for s in GLOBAL_STATUSES:
        doc.append("stages", {"stage_name": s, "maps_to": s, "color": colors[s]})
    doc.insert(ignore_permissions=True)
    return doc.name
