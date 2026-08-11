"""Backfill lead time on tickets that were already resolved.

Lead time (raised → resolved) is recoverable for every historical ticket,
because both stamps have always been recorded. Cycle time is not: nothing
ever recorded when a ticket left the queue, so old tickets keep an empty
cycle_time_hours instead of a guessed one. That gap closes on its own as new
tickets flow through — an invented number would poison the first months of
any trend built on it.
"""
import frappe


def execute():
    if not frappe.db.table_exists("Hub Ticket"):
        return
    frappe.db.sql(
        """UPDATE `tabHub Ticket`
           SET lead_time_hours = ROUND(
                 TIMESTAMPDIFF(SECOND, creation, resolved_on) / 3600, 2)
           WHERE resolved_on IS NOT NULL
             AND resolved_on >= creation
             AND lead_time_hours IS NULL""")
    frappe.db.commit()
