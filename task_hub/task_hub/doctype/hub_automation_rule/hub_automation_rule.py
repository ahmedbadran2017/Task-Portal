"""User-defined automation rules — the Hub's "when X then Y" engine.

Managers compose rules from Settings (no code): a trigger over open tickets
plus one action. `run_automation_rules` evaluates hourly; each rule fires at
most once per ticket (tracked in fired_log) so people aren't nagged.
"""
import json

import frappe
from frappe import _
from frappe.model.document import Document

OPEN_STATES = ("Open", "In Progress", "In Review")
FIRED_CAP = 2000  # keep the log bounded; oldest entries rotate out


class HubAutomationRule(Document):
    def validate(self):
        if self.action in ("Notify user", "Assign to user") and not self.action_user:
            frappe.throw(_("This action needs a user."))
        if self.action == "Set priority" and not self.action_priority:
            frappe.throw(_("This action needs a priority."))
        if self.trigger == "Stuck in stage":
            self.stuck_days = max(1, min(90, int(self.stuck_days or 3)))


def _matches(rule):
    """Open tickets the rule's trigger currently selects."""
    conds = ["status IN ('Open', 'In Progress', 'In Review')"]
    params = {}
    if rule.workspace:
        conds.append("workspace = %(ws)s")
        params["ws"] = rule.workspace
    if rule.trigger == "Stuck in stage":
        conds.append("TIMESTAMPDIFF(DAY, modified, NOW()) >= %(days)s")
        params["days"] = int(rule.stuck_days or 3)
    elif rule.trigger == "Due date passed":
        conds.append("due_date IS NOT NULL AND due_date < CURDATE()")
    # Deterministic order: an unordered LIMIT meant some matching tickets
    # could never be reached at all.
    return frappe.db.sql(
        f"""SELECT name, title, workspace, assigned_to, reported_by
            FROM `tabHub Ticket` WHERE {' AND '.join(conds)}
            ORDER BY modified ASC LIMIT 500""",
        params, as_dict=True,
    )


def _apply(rule, tk):
    from task_hub.notify import push

    label = _("Automation: {0}").format(rule.rule_name)
    if rule.action == "Notify workspace managers":
        # Now that boards name their leads, this action can finally mean what
        # it says: it used to blast every holder of a manager ROLE company-wide,
        # which had nothing to do with the ticket's workspace.
        from task_hub.api.utils import MANAGER_ROLES
        from task_hub.task_hub.doctype.hub_workspace.hub_workspace import (
            workspace_leads)
        targets = set()
        if tk.workspace:
            try:
                targets = set(workspace_leads(tk.workspace))
            except Exception:
                targets = set()
        if not targets:
            # Board has no lead yet — fall back to the hub's managers rather
            # than dropping the alert on the floor.
            targets = {r.parent for r in frappe.get_all(
                "Has Role",
                filters={"role": ["in", list(MANAGER_ROLES)], "parenttype": "User"},
                fields=["parent"])}
        for user in targets:
            push(user, tk.name, "sla_warning", f"{label} — {tk.title}")
    elif rule.action == "Notify user":
        push(rule.action_user, tk.name, "sla_warning", f"{label} — {tk.title}")
    elif rule.action == "Assign to user":
        if not tk.assigned_to:
            doc = frappe.get_doc("Hub Ticket", tk.name)
            doc.assigned_to = rule.action_user
            doc.save(ignore_permissions=True)
    elif rule.action == "Set priority":
        doc = frappe.get_doc("Hub Ticket", tk.name)
        if doc.priority != rule.action_priority:
            doc.priority = rule.action_priority
            doc.save(ignore_permissions=True)


def run_automation_rules():
    """Hourly scheduler — evaluate every active rule, once per ticket."""
    if not frappe.db.table_exists("Hub Automation Rule"):
        return
    for name in frappe.get_all("Hub Automation Rule", filters={"active": 1},
                               pluck="name"):
        rule = frappe.get_doc("Hub Automation Rule", name)
        try:
            fired = set(json.loads(rule.fired_log or "[]"))
        except Exception:
            fired = set()
        changed = False
        for tk in _matches(rule):
            if tk.name in fired:
                continue
            try:
                _apply(rule, tk)
            except Exception:
                frappe.log_error(title=f"Hub automation rule {rule.name}",
                                 message=frappe.get_traceback()[:3000])
                continue
            fired.add(tk.name)
            changed = True
        if changed:
            # Prune by liveness, not by age: dropping the oldest entries made
            # a long-lived ticket fire the same rule a second time. Closed
            # tickets can't match again, so their keys are safe to forget.
            if len(fired) > FIRED_CAP:
                still_open = set(frappe.get_all(
                    "Hub Ticket",
                    filters={"name": ["in", list(fired)],
                             "status": ["in", OPEN_STATES]},
                    pluck="name"))
                fired = still_open or set(list(fired)[-FIRED_CAP:])
            frappe.db.set_value("Hub Automation Rule", rule.name, "fired_log",
                                json.dumps(sorted(fired)),
                                update_modified=False)
            frappe.db.commit()  # per rule — one bad rule can't undo the rest
