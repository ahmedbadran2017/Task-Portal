"""Workspace management + per-workspace board data."""
import json

import frappe
from frappe import _

from task_hub.api.utils import gate_read, gate_manager, visibility_sql
from task_hub.task_hub.doctype.hub_workspace.hub_workspace import (
    ensure_default_workspace, workspace_members, workspace_leads,
    GLOBAL_STATUSES)

OPEN_STATES = ("Open", "In Progress", "In Review")


def _open_counts():
    """Open-ticket count per workspace in ONE grouped query, scoped to what
    the caller may see (the per-workspace version was an N+1 on every SPA
    navigation)."""
    vis, params = visibility_sql()
    rows = frappe.db.sql(
        f"""SELECT workspace, COUNT(*) n FROM `tabHub Ticket`
            WHERE status IN ('Open', 'In Progress', 'In Review'){vis}
            GROUP BY workspace""",
        params, as_dict=True,
    )
    return {r.workspace: r.n for r in rows}


@frappe.whitelist()
def list_workspaces():
    """All workspaces with stages, member counts, and open-ticket counts.
    Whole-company transparency: everyone sees every workspace; membership
    only drives defaults."""
    gate_read()
    ensure_default_workspace()
    user = frappe.session.user

    out = []
    counts = _open_counts()
    for name in frappe.get_all("Hub Workspace", pluck="name",
                               order_by="is_default desc, creation asc"):
        ws = frappe.get_cached_doc("Hub Workspace", name)
        members = workspace_members(name)
        leads = workspace_leads(name)
        out.append({
            "name": ws.name,
            "icon": ws.icon or "🗂️",
            "color": ws.color or "#d45d3e",
            "department": ws.department,
            "extra_members": ws.extra_members or "",
            "leads": ws.get("leads") or "",
            "is_lead": user in leads,
            "use_sla": ws.use_sla,
            "track_source_portal": ws.track_source_portal,
            "is_default": ws.is_default,
            "is_member": user in members,
            "members": members,
            "member_count": len(members),
            "open_count": counts.get(ws.name, 0),
            "stages": [
                {"stage_name": s.stage_name, "maps_to": s.maps_to,
                 "color": s.color or "#78716c"}
                for s in ws.stages
            ],
        })
    return out


@frappe.whitelist()
def save_workspace(**kwargs):
    """Create (no name) or update (with name) a workspace. `stages` arrives
    as a JSON list of {stage_name, maps_to, color}."""
    gate_manager()
    name = kwargs.get("name")
    doc = (frappe.get_doc("Hub Workspace", name)
           if name else frappe.new_doc("Hub Workspace"))

    if not name and kwargs.get("workspace_name"):
        doc.workspace_name = kwargs["workspace_name"].strip()
    for f in ("icon", "color", "department", "extra_members", "leads"):
        if f in kwargs and kwargs[f] is not None:
            doc.set(f, kwargs[f] or None)
    for flag in ("use_sla", "track_source_portal"):
        if flag in kwargs:
            doc.set(flag, 1 if kwargs[flag] in (1, "1", True, "true") else 0)

    stages = kwargs.get("stages")
    if stages:
        if isinstance(stages, str):
            stages = json.loads(stages)
        doc.stages = []
        for s in stages:
            if not (s.get("stage_name") or "").strip():
                continue
            maps_to = s.get("maps_to") if s.get("maps_to") in GLOBAL_STATUSES else "Open"
            doc.append("stages", {
                "stage_name": s["stage_name"].strip()[:60],
                "maps_to": maps_to,
                "color": (s.get("color") or "")[:9] or None,
            })
    doc.save(ignore_permissions=True)

    # Stages may have been renamed/removed — re-slot any ticket whose stage
    # vanished onto the stage matching its canonical status, so boards never
    # show orphaned cards.
    valid = [s.stage_name for s in doc.stages]
    if valid:
        from task_hub.task_hub.doctype.hub_workspace.hub_workspace import stage_for_status
        orphans = frappe.get_all(
            "Hub Ticket",
            filters={"workspace": doc.name, "stage": ["not in", valid]},
            fields=["name", "status"])
        for o in orphans:
            frappe.db.set_value("Hub Ticket", o.name, "stage",
                                stage_for_status(doc, o.status),
                                update_modified=False)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def delete_workspace(name):
    """Delete a workspace; its tickets move to the default one."""
    gate_manager()
    ws = frappe.get_doc("Hub Workspace", name)
    if ws.is_default:
        frappe.throw(_("The default workspace can't be deleted."))
    default = ensure_default_workspace()
    frappe.db.sql(
        """UPDATE `tabHub Ticket` SET workspace = %s, stage = status
           WHERE workspace = %s""", (default, name))
    frappe.delete_doc("Hub Workspace", name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": name, "tickets_moved_to": default}


@frappe.whitelist()
def move_stage(name, stage):
    """Move a ticket to a workspace stage — sets both the stage and the
    canonical status it maps to, so the whole engine follows."""
    gate_read()
    from task_hub.api.tickets import _load_editable

    doc = _load_editable(name)
    if not doc.workspace:
        frappe.throw(_("Ticket has no workspace."))
    ws = frappe.get_cached_doc("Hub Workspace", doc.workspace)
    match = next((s for s in ws.stages if s.stage_name == stage), None)
    if not match:
        frappe.throw(_("Stage {0} doesn't exist in {1}.").format(stage, ws.name))
    doc.stage = stage
    doc.status = match.maps_to
    doc.flags.stage_set_explicitly = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "stage": doc.stage, "status": doc.status}


@frappe.whitelist()
def set_ticket_workspace(name, workspace):
    """Move a ticket between workspaces (stage resets to the matching one)."""
    gate_read()
    from task_hub.api.tickets import _load_editable
    from task_hub.task_hub.doctype.hub_workspace.hub_workspace import stage_for_status

    doc = _load_editable(name)
    if not frappe.db.exists("Hub Workspace", workspace):
        frappe.throw(_("Unknown workspace."))
    ws = frappe.get_cached_doc("Hub Workspace", workspace)
    doc.workspace = workspace
    doc.stage = stage_for_status(ws, doc.status)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "workspace": doc.workspace, "stage": doc.stage}


@frappe.whitelist()
def list_departments():
    """Every real department, with its active headcount — for the workspace form.

    Driven by `tabDepartment`, not by grouping `tabEmployee`: the old query
    could only ever list departments that already had staff, so a real team
    like Media Buying (whose people are filed under Marketing in HR) was
    simply absent from the picker with no explanation. Now it shows with
    `employees = 0`, and the form offers the manual member list instead.

    Group nodes (the tree's folders, e.g. "All Departments") are skipped —
    employees are never filed against them.
    """
    # Managers only: the rows carry members' login ids, which is more than a
    # regular user needs, and the workspace form is manager-only anyway.
    gate_manager()
    counts = {}
    logins = {}
    # HR docs are permission-gated per department; the picker needs the whole
    # org chart, so read it as the system (the endpoint itself is the gate).
    for r in frappe.get_all(
        "Employee", filters={"status": "Active", "department": ["is", "set"]},
        fields=["department", "user_id"], limit_page_length=0,
        ignore_permissions=True,
    ):
        counts[r.department] = counts.get(r.department, 0) + 1
        if r.user_id:
            logins.setdefault(r.department, []).append(r.user_id)

    meta = frappe.get_meta("Department")
    filters = {}
    if meta.has_field("is_group"):
        filters["is_group"] = 0
    if meta.has_field("disabled"):
        filters["disabled"] = 0
    names = frappe.get_all("Department", filters=filters, pluck="name",
                           limit_page_length=0, ignore_permissions=True)

    # A department row can go missing from the tree while its employees keep
    # pointing at it; keep those visible rather than silently dropping people.
    for orphan in set(counts) - set(names):
        names.append(orphan)

    # `members` (people with a login) is what the workspace actually inherits;
    # `employees` is raw headcount, which can be higher.
    rows = [{"name": n, "employees": counts.get(n, 0),
             "members": sorted(logins.get(n, []))} for n in names]
    rows.sort(key=lambda r: (-r["employees"], r["name"]))
    return rows
