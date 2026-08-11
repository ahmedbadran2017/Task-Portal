"""Turn the source-portal question off on every board except the cross-portal
intake one.

"Which portal did this come from?" is a technical-support question: a bug can
arrive from Supplier, Logistics, the website, WhatsApp. A Media Buying task or
a Design request has no such origin — the field was pure noise there, and once
it became mandatory it was noise you couldn't skip.

The doctype default is 1, so a workspace created after this patch keeps asking
until a manager turns it off; this only clears the boards that already exist.
Boards whose portal was already answered keep their stored values — the field
stops being asked for, it isn't erased.
"""
import frappe


def execute():
    if not frappe.db.table_exists("Hub Workspace"):
        return
    # Cross-portal intake = the default workspace (Technical Support). Every
    # other board belongs to one department and receives work from inside it.
    frappe.db.sql(
        """UPDATE `tabHub Workspace`
           SET track_source_portal = 0
           WHERE COALESCE(is_default, 0) = 0""")
    frappe.db.commit()
