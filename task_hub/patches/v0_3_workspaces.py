"""Backfill: every existing ticket joins the default 'Technical Support'
workspace with stage = its current status."""
import frappe


def execute():
    if not frappe.db.table_exists("Hub Ticket") or not frappe.db.table_exists("Hub Workspace"):
        return
    from task_hub.task_hub.doctype.hub_workspace.hub_workspace import ensure_default_workspace
    default = ensure_default_workspace()
    frappe.db.sql(
        """UPDATE `tabHub Ticket`
           SET workspace = %s, stage = status
           WHERE workspace IS NULL OR workspace = ''""", (default,))
    frappe.db.commit()
