"""Seed one workspace per real operating department (Phase 1 of the
company-wide rollout), including the Marketing flow that v0_4 tried to seed —
that patch ran pre-model-sync, so on the first migrate the Hub Workspace
table didn't exist yet and it returned silently. This one is registered
under [post_model_sync].

Idempotent: a department that already owns a workspace (or a name that's
taken) is skipped, so manager edits and deletions are never overwritten.
"""
import frappe

MARKETING_STAGES = [
    ("فكرة", "Open", "#3b82f6"),
    ("Brief", "In Progress", "#0891b2"),
    ("تصميم", "In Progress", "#d97706"),
    ("مراجعة", "In Review", "#7c3aed"),
    ("منشور", "Resolved", "#059669"),
]

SERVICE_STAGES = [
    ("New", "Open", "#3b82f6"),
    ("Working", "In Progress", "#0891b2"),
    ("Waiting / Review", "In Review", "#d97706"),
    ("Done", "Resolved", "#059669"),
]

CONTENT_STAGES = [
    ("Backlog", "Open", "#3b82f6"),
    ("In Production", "In Progress", "#0891b2"),
    ("Review", "In Review", "#7c3aed"),
    ("Published", "Resolved", "#059669"),
]

DESIGN_STAGES = [
    ("Request", "Open", "#3b82f6"),
    ("Designing", "In Progress", "#d97706"),
    ("Review", "In Review", "#7c3aed"),
    ("Delivered", "Resolved", "#059669"),
]

# (name, icon, color, department, use_sla, stages)
SEED = [
    ("Customer Service", "🎧", "#0d9488", "Customer Service - JM", 1, SERVICE_STAGES),
    ("Logistics", "🚚", "#2563eb", "Logistics - JM", 1, SERVICE_STAGES),
    ("Shipping & Delivery", "📦", "#b45309", "Shipping & Delivery Department - JM", 1, SERVICE_STAGES),
    ("Purchasing", "🛒", "#d97706", "Purchase - JM", 1, SERVICE_STAGES),
    ("Content & Ecommerce", "🛍️", "#4f46e5", "Ecommerce - ML", 0, CONTENT_STAGES),
    ("Design", "🎨", "#7c3aed", "Designing - ML", 0, DESIGN_STAGES),
    ("Marketing", "📣", "#db2777", "Marketing - JM", 0, MARKETING_STAGES),
]


def execute():
    if not frappe.db.table_exists("Hub Workspace"):
        return

    for name, icon, color, department, use_sla, stages in SEED:
        if not frappe.db.exists("Department", department):
            continue
        if frappe.db.exists("Hub Workspace", name):
            continue
        if frappe.db.exists("Hub Workspace", {"department": department}):
            continue

        doc = frappe.new_doc("Hub Workspace")
        doc.workspace_name = name
        doc.icon = icon
        doc.color = color
        doc.department = department
        doc.use_sla = use_sla
        if name == "Marketing":
            # ML marketers join the JM marketing board as extra members.
            extras = [r.user_id for r in frappe.get_all(
                "Employee",
                filters={"status": "Active", "department": "Marketing - ML",
                         "user_id": ["is", "set"]},
                fields=["user_id"])]
            if extras:
                doc.extra_members = ", ".join(extras)
        for stage, maps_to, stage_color in stages:
            doc.append("stages", {"stage_name": stage, "maps_to": maps_to,
                                  "color": stage_color})
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
