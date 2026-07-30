"""Seed the Marketing workspace with the team's real flow:
فكرة → Brief → تصميم → مراجعة → منشور

Runs once; if the team later reshapes it from Settings → Workspaces the
patch never overwrites their edits (exists-check only).
"""
import frappe


def execute():
    if not frappe.db.table_exists("Hub Workspace"):
        return
    if frappe.db.exists("Hub Workspace", "Marketing"):
        return

    doc = frappe.new_doc("Hub Workspace")
    doc.workspace_name = "Marketing"
    doc.icon = "📣"
    doc.color = "#db2777"
    doc.use_sla = 0  # creative flow — deadlines live on due dates, not priorities

    # Membership: Marketing - JM as the base department, ML marketers as extras.
    if frappe.db.exists("Department", "Marketing - JM"):
        doc.department = "Marketing - JM"
    extras = [r.user_id for r in frappe.get_all(
        "Employee",
        filters={"status": "Active", "department": "Marketing - ML",
                 "user_id": ["is", "set"]},
        fields=["user_id"])]
    if extras:
        doc.extra_members = ", ".join(extras)

    for stage, maps_to, color in [
        ("فكرة", "Open", "#3b82f6"),
        ("Brief", "In Progress", "#0891b2"),
        ("تصميم", "In Progress", "#d97706"),
        ("مراجعة", "In Review", "#7c3aed"),
        ("منشور", "Resolved", "#059669"),
    ]:
        doc.append("stages", {"stage_name": stage, "maps_to": maps_to, "color": color})

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
