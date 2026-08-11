"""
Hub Ticket CRUD + workflow API.

`create_ticket` is the ONE entrypoint every portal calls (from its Vue
frontend or server-side) to raise a task/problem/request. Everything else
here powers the central Hub SPA.
"""
import json

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.file_manager import save_file

from task_hub.api.utils import (
    gate_read, can_edit_ticket, require_portal, visibility_sql,
    can_view_ticket, gate_view, safe_url,
    VALID_TYPES, VALID_PRIORITIES, VALID_STATUSES,
)

# Hard ceiling on any single page — an unbounded `limit` would let one
# request pull the whole table.
MAX_PAGE = 1000


def _load_viewable(name):
    """Load a ticket the caller is allowed to see (reporter/assignee/
    watcher/manager)."""
    return gate_view(frappe.get_doc("Hub Ticket", name))


LIST_FIELDS = [
    "name", "title", "ticket_type", "priority", "status",
    "source_portal", "department", "reported_by", "assigned_to",
    "due_date", "sla_deadline", "sla_breached", "resolved_on",
    "linked_label", "linked_url", "creation", "modified",
    "workspace", "stage", "blocked_by",
]


def _as_dict(payload):
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return {}
    return payload or {}


# --------------------------------------------------------------------- create
@frappe.whitelist()
def create_ticket(**kwargs):
    """Universal ticket creation — called by every portal.

    Accepts either flat kwargs or a single `payload` JSON blob. Recognised
    keys: title, description, ticket_type, priority, source_portal,
    department, assigned_to, due_date, tags, linked_doctype, linked_name,
    linked_label, linked_url.
    """
    gate_read()
    data = _as_dict(kwargs.get("payload")) if kwargs.get("payload") else dict(kwargs)

    title = (data.get("title") or "").strip()
    if not title:
        frappe.throw(_("A ticket title is required."))

    # Fall back to admin-configured defaults, then hard defaults.
    try:
        s = frappe.get_cached_doc("Task Hub Settings")
        default_type = s.default_ticket_type or "Task"
        default_priority = s.default_priority or "Medium"
    except Exception:
        default_type, default_priority = "Task", "Medium"

    ticket_type = data.get("ticket_type") if data.get("ticket_type") in VALID_TYPES else default_type
    priority = data.get("priority") if data.get("priority") in VALID_PRIORITIES else default_priority

    assigned_to = data.get("assigned_to") or None
    if assigned_to and not frappe.db.exists("User", assigned_to):
        assigned_to = None  # silently drop unknown assignees rather than failing the report

    # The board decides whether the portal question is even asked, so it has
    # to be resolved before the portal is validated.
    target_ws = data.get("workspace")
    if target_ws and not frappe.db.exists("Hub Workspace", target_ws):
        target_ws = None

    doc = frappe.new_doc("Hub Ticket")
    doc.title = title[:180]
    doc.description = data.get("description") or ""
    doc.ticket_type = ticket_type
    doc.priority = priority
    doc.source_portal = require_portal(data.get("source_portal"), target_ws)
    doc.department = data.get("department") or None
    doc.assigned_to = assigned_to
    doc.due_date = data.get("due_date") or None
    doc.tags = data.get("tags") or None
    doc.linked_doctype = data.get("linked_doctype") or None
    doc.linked_name = data.get("linked_name") or None
    doc.linked_label = data.get("linked_label") or None
    doc.linked_url = safe_url(data.get("linked_url"))
    if target_ws:
        doc.workspace = target_ws
    doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"name": doc.name, "title": doc.title, "status": doc.status}


# ----------------------------------------------------------------------- read
@frappe.whitelist()
def list_tickets(status=None, priority=None, source_portal=None,
                 assigned_to=None, reported_by=None, ticket_type=None,
                 department=None, workspace=None, search=None, breached_only=0,
                 mine=0, unassigned=0, due_from=None, due_to=None,
                 limit=100, start=0, order_by="modified desc"):
    """Filtered ticket list for the Hub board / list views.

    Non-managers only ever see their own tickets (reporter, assignee, or
    watcher) — the visibility fragment ANDs with every other filter, so it
    composes with search unlike frappe.get_all's single or_filters group.

    `mine` is a scope, not a flag: "assigned", "reported", or anything truthy
    for both (the default, and what a bare `mine=1` deep link means).
    """
    gate_read()
    conds, params = ["1=1"], {}

    def eq(field, value):
        conds.append(f"{field} = %({field})s")
        params[field] = value

    if status:
        eq("status", status)
    if department:
        eq("department", department)
    if workspace:
        eq("workspace", workspace)
    if due_from:
        conds.append("due_date >= %(due_from)s")
        params["due_from"] = due_from
    if due_to:
        conds.append("due_date <= %(due_to)s")
        params["due_to"] = due_to
    if int(unassigned or 0):
        conds.append("COALESCE(assigned_to, '') = ''")
    if priority:
        eq("priority", priority)
    if source_portal:
        eq("source_portal", source_portal)
    if ticket_type:
        eq("ticket_type", ticket_type)
    if assigned_to:
        eq("assigned_to", assigned_to)
    if reported_by:
        eq("reported_by", reported_by)
    if int(breached_only or 0):
        conds.append("sla_breached = 1")
    # "Mine" used to mean assigned_to only, which quietly hid every ticket you
    # raised and handed to someone else — you could no longer find your own
    # request. It now defaults to both sides of the handover, matching the
    # in-portal panel's `my_tasks` scopes; pass "assigned"/"reported" to narrow.
    mine_scope = str(mine or "").strip().lower()
    if mine_scope in ("0", "false", "none"):
        mine_scope = ""
    if mine_scope:
        if mine_scope == "assigned":
            conds.append("assigned_to = %(mine_user)s")
        elif mine_scope == "reported":
            conds.append("reported_by = %(mine_user)s")
        else:
            conds.append(
                "(assigned_to = %(mine_user)s OR reported_by = %(mine_user)s)")
        params["mine_user"] = frappe.session.user
    if search:
        conds.append("(title LIKE %(search)s OR name LIKE %(search)s)")
        params["search"] = f"%{search}%"

    vis, vis_params = visibility_sql()
    params.update(vis_params)

    # Whitelist order_by to avoid injection through the SPA.
    allowed_order = {
        "modified desc", "modified asc", "creation desc", "creation asc",
        "priority asc", "due_date asc", "sla_deadline asc",
    }
    order_by = order_by if order_by in allowed_order else "modified desc"

    where = " AND ".join(conds) + vis
    fields = ", ".join(f"`{f}`" for f in LIST_FIELDS)
    params.update(limit=max(1, min(MAX_PAGE, int(limit))), start=max(0, int(start)))
    rows = frappe.db.sql(
        f"""SELECT {fields} FROM `tabHub Ticket` WHERE {where}
            ORDER BY {order_by} LIMIT %(limit)s OFFSET %(start)s""",
        params, as_dict=True,
    )
    total = frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabHub Ticket` WHERE {where}", params,
    )[0][0]
    return {"tickets": rows, "total": total}


@frappe.whitelist()
def get_ticket(name):
    """Full ticket incl. comments, activity timeline, and attachments."""
    gate_read()
    doc = _load_viewable(name)
    d = doc.as_dict()
    return {
        "ticket": {k: d.get(k) for k in (LIST_FIELDS + [
            "description", "tags", "linked_doctype", "linked_name",
        ])},
        "comments": [
            {"author": c.author, "comment_on": c.comment_on, "message": c.message}
            for c in doc.comments
        ],
        "activity": [
            {"activity_on": a.activity_on, "actor": a.actor,
             "action": a.action, "detail": a.detail}
            for a in doc.activity
        ],
        "attachments": _attachments(name),
        "checklist": [
            {"name": c.name, "item": c.item, "done": c.done, "done_by": c.done_by}
            for c in doc.checklist
        ],
        "watchers": doc.watcher_list(),
        "watching": frappe.session.user in doc.watcher_list(),
        "blocker": _blocker_info(doc.blocked_by),
        "blocking": _blocking(name),
    }


def _blocking(name):
    """Open tickets waiting on this one — scoped, so a reporter doesn't read
    other departments' titles through their own ticket."""
    vis, params = visibility_sql()
    params["blocked_by"] = name
    return frappe.db.sql(
        f"""SELECT name, title, status FROM `tabHub Ticket`
            WHERE blocked_by = %(blocked_by)s
              AND status IN ('Open', 'In Progress', 'In Review'){vis}
            ORDER BY modified DESC LIMIT 20""",
        params, as_dict=True,
    )


def _blocker_info(blocked_by):
    if not blocked_by:
        return None
    row = frappe.db.get_value("Hub Ticket", blocked_by,
                              ["name", "title", "status"], as_dict=True)
    return row


@frappe.whitelist()
def set_blocked_by(name, blocked_by=None):
    """Link (or clear) the ticket this one is waiting on."""
    gate_read()
    if not can_edit_ticket(name):
        frappe.throw(_("Only the reporter, assignee, or a manager can edit this ticket."),
                     frappe.PermissionError)
    doc = frappe.get_doc("Hub Ticket", name)
    blocked_by = (blocked_by or "").strip() or None
    if blocked_by:
        if blocked_by == name:
            frappe.throw(_("A ticket can't block itself."))
        if not frappe.db.exists("Hub Ticket", blocked_by):
            frappe.throw(_("Ticket {0} was not found.").format(blocked_by))
        # No two-node cycles either — A waits on B while B waits on A.
        if frappe.db.get_value("Hub Ticket", blocked_by, "blocked_by") == name:
            frappe.throw(_("These tickets would block each other."))
    doc.blocked_by = blocked_by
    doc.append("activity", {
        "activity_on": now_datetime(),
        "actor": frappe.session.user,
        "action": "Dependency",
        "detail": (_("Blocked by {0}").format(blocked_by) if blocked_by
                   else _("Dependency cleared")),
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "blocked_by": doc.blocked_by,
            "blocker": _blocker_info(doc.blocked_by)}


def _attachments(name):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Hub Ticket", "attached_to_name": name},
        fields=["name", "file_name", "file_url", "file_size", "is_private",
                "owner", "creation"],
        order_by="creation asc",
    )


# --------------------------------------------------------------------- mutate
def _load_editable(name):
    doc = frappe.get_doc("Hub Ticket", name)
    if not can_edit_ticket(doc):
        frappe.throw(_("You can't modify this ticket."), frappe.PermissionError)
    return doc


@frappe.whitelist()
def update_ticket(name, title=None, description=None, due_date=None, tags=None):
    """Edit the ticket's core fields — reporter, assignee, or managers."""
    gate_read()
    doc = _load_editable(name)
    changes = []
    if title is not None and title.strip() and title.strip() != doc.title:
        changes.append(f"title: “{doc.title}” → “{title.strip()[:80]}”")
        doc.title = title.strip()[:180]
    if description is not None and description != doc.description:
        changes.append("description updated")
        doc.description = description
    if due_date is not None and (due_date or None) != (str(doc.due_date) if doc.due_date else None):
        changes.append(f"due date → {due_date or '—'}")
        doc.due_date = due_date or None
    if tags is not None and (tags or None) != doc.tags:
        doc.tags = tags or None
    if changes:
        doc.append("activity", {
            "activity_on": now_datetime(),
            "actor": frappe.session.user,
            "action": "Edited",
            "detail": "; ".join(changes)[:500],
        })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "title": doc.title, "due_date": doc.due_date}


@frappe.whitelist()
def watch_ticket(name, watch=1):
    """Follow/unfollow a ticket — watchers get in-app updates on status
    changes and comments."""
    gate_read()
    # Watching grants read access, so it must never be self-service on a
    # ticket the caller can't already see.
    doc = _load_viewable(name)
    user = frappe.session.user
    watchers = set(doc.watcher_list())
    if int(watch or 0):
        watchers.add(user)
    else:
        watchers.discard(user)
    doc.watchers = ", ".join(sorted(watchers))
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "watching": user in watchers,
            "watchers": sorted(watchers)}


@frappe.whitelist()
def checklist_add(name, item):
    gate_read()
    item = (item or "").strip()
    if not item:
        frappe.throw(_("Checklist item cannot be empty."))
    doc = _load_viewable(name)  # participants may contribute
    doc.append("checklist", {"item": item[:200], "done": 0})
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _checklist(doc)


@frappe.whitelist()
def checklist_toggle(name, row):
    gate_read()
    doc = _load_viewable(name)
    for c in doc.checklist:
        if c.name == row:
            c.done = 0 if c.done else 1
            c.done_by = frappe.session.user if c.done else None
            break
    else:
        frappe.throw(_("Checklist item not found."))
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _checklist(doc)


@frappe.whitelist()
def checklist_remove(name, row):
    gate_read()
    doc = _load_editable(name)
    doc.checklist = [c for c in doc.checklist if c.name != row]
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _checklist(doc)


def _checklist(doc):
    return {"checklist": [
        {"name": c.name, "item": c.item, "done": c.done, "done_by": c.done_by}
        for c in doc.checklist
    ]}


@frappe.whitelist()
def update_status(name, status):
    gate_read()
    if status not in VALID_STATUSES:
        frappe.throw(_("Invalid status: {0}").format(status))
    doc = _load_editable(name)
    doc.status = status
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status, "resolved_on": doc.resolved_on}


@frappe.whitelist()
def assign_ticket(name, assigned_to=None):
    gate_read()
    doc = _load_editable(name)
    if assigned_to and not frappe.db.exists("User", assigned_to):
        frappe.throw(_("Unknown user: {0}").format(assigned_to))
    doc.assigned_to = assigned_to or None
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "assigned_to": doc.assigned_to}


@frappe.whitelist()
def set_priority(name, priority):
    gate_read()
    if priority not in VALID_PRIORITIES:
        frappe.throw(_("Invalid priority: {0}").format(priority))
    doc = _load_editable(name)
    doc.priority = priority
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "priority": doc.priority, "sla_deadline": doc.sla_deadline}


ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "svg", "heic",
    "pdf", "csv", "xlsx", "xls", "docx", "doc", "txt", "zip",
    "mp4", "mov", "webm",
}
MAX_FILE_MB = 20


@frappe.whitelist()
def upload_attachment(name):
    """Attach an uploaded file (multipart field `file`) to a Hub Ticket.

    Participants only — same policy as commenting.
    """
    gate_read()
    doc = _load_viewable(name)

    f = frappe.request.files.get("file")
    if not f or not f.filename:
        frappe.throw(_("No file was uploaded."))

    ext = (f.filename.rsplit(".", 1)[-1] or "").lower()
    if ext not in ALLOWED_EXTENSIONS:
        frappe.throw(_("File type .{0} is not allowed.").format(ext))

    content = f.stream.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        frappe.throw(_("File is larger than {0} MB.").format(MAX_FILE_MB))

    # Private: customer screenshots must not be world-readable. The SPA and
    # portals request them with the session cookie, so previews still render.
    file_doc = save_file(f.filename, content, "Hub Ticket", doc.name,
                         is_private=1)

    doc.append("activity", {
        "activity_on": now_datetime(),
        "actor": frappe.session.user,
        "action": "Attachment added",
        "detail": f.filename,
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {
        "name": file_doc.name,
        "file_name": file_doc.file_name,
        "file_url": file_doc.file_url,
        "file_size": file_doc.file_size,
    }


@frappe.whitelist()
def delete_attachment(name, file_id):
    """Remove an attachment — allowed for the uploader or ticket editors."""
    gate_read()
    row = frappe.db.get_value(
        "File", file_id,
        ["name", "file_name", "attached_to_doctype", "attached_to_name", "owner"],
        as_dict=True,
    )
    if not row or row.attached_to_doctype != "Hub Ticket" or row.attached_to_name != name:
        frappe.throw(_("Attachment not found on this ticket."))
    if row.owner != frappe.session.user and not can_edit_ticket(name):
        frappe.throw(_("You can't remove this attachment."), frappe.PermissionError)

    frappe.delete_doc("File", row.name, ignore_permissions=True)

    doc = frappe.get_doc("Hub Ticket", name)
    doc.append("activity", {
        "activity_on": now_datetime(),
        "actor": frappe.session.user,
        "action": "Attachment removed",
        "detail": row.file_name,
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": row.name}


@frappe.whitelist()
def add_comment(name, message):
    gate_read()
    message = (message or "").strip()
    if not message:
        frappe.throw(_("Comment cannot be empty."))
    doc = _load_viewable(name)  # participants only — comments are emailed out
    doc.append("comments", {
        "author": frappe.session.user,
        "comment_on": now_datetime(),
        "message": message[:2000],
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    _notify_comment(doc, message)
    return {"name": doc.name, "count": len(doc.comments)}


def _resolve_mentions(message):
    """@<email-local-part> tokens → matching enabled System Users.
    Ambiguous or unknown tokens are ignored."""
    import re

    tokens = set(re.findall(r"@([A-Za-z0-9._-]+)", message))
    if not tokens:
        return set()
    # Only fetch users whose local part could match a token in this comment,
    # instead of loading every system user on every comment.
    by_local = {}
    or_filters = [["name", "like", f"{tok}@%"] for tok in tokens]
    for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"},
                            or_filters=or_filters, fields=["name"],
                            limit_page_length=200):
        by_local.setdefault(u.name.split("@")[0].lower(), []).append(u.name)
    found = set()
    for token in tokens:
        matches = by_local.get(token.lower()) or []
        if len(matches) == 1:
            found.add(matches[0])
    return found


def _notify_comment(doc, message):
    """Mentions get a mention notice; the other participants (assignee +
    reporter) get a comment notice. The commenter is never notified."""
    from task_hub.notify import push

    author = frappe.session.user
    author_name = frappe.utils.get_fullname(author)
    quoted = frappe.utils.escape_html(message)

    mentioned = _resolve_mentions(message) - {author}
    for user in mentioned:
        push(
            user, doc.name, "mention",
            _("{0} mentioned you: {1}").format(author_name, message[:120]),
            email_subject=_("[Task Hub] You were mentioned on {0}").format(doc.name),
            email_html=(f"<p>{author_name} mentioned you on <b>{doc.title}</b>:</p>"
                        f"<blockquote>{quoted}</blockquote>"),
        )

    participants = {doc.assigned_to, doc.reported_by} - {author, None, ""} - mentioned
    for user in participants:
        push(
            user, doc.name, "comment",
            _("{0} commented on {1}: {2}").format(author_name, doc.name, message[:120]),
            email_subject=_("[Task Hub] New comment on {0}").format(doc.name),
            email_html=(f"<p>{author_name} commented on "
                        f"<b>{frappe.utils.escape_html(doc.title)}</b>:</p>"
                        f"<blockquote>{quoted}</blockquote>"),
        )

    # Watchers follow along in-app only — no email.
    for user in set(doc.watcher_list()) - {author} - mentioned - participants:
        push(user, doc.name, "comment",
             _("{0} commented on {1}: {2}").format(author_name, doc.name, message[:120]))


@frappe.whitelist()
def find_similar(title):
    """Open tickets that look like the one being written — shown in the
    create modal before a duplicate is born. Lexical match on title words,
    scoped by the caller's visibility."""
    gate_read()
    words = [w.strip() for w in (title or "").split() if len(w.strip()) >= 3][:4]
    if not words:
        return []
    vis, params = visibility_sql()
    conds = " OR ".join(f"title LIKE %(w{i})s" for i in range(len(words)))
    params.update({f"w{i}": f"%{w}%" for i, w in enumerate(words)})
    return frappe.db.sql(
        f"""SELECT name, title, status, workspace FROM `tabHub Ticket`
            WHERE status IN ('Open', 'In Progress', 'In Review')
              AND ({conds}){vis}
            ORDER BY modified DESC LIMIT 3""",
        params, as_dict=True,
    )


@frappe.whitelist()
def delete_ticket(name):
    """Permanently remove a ticket — the escape hatch for a mistaken entry.

    Allowed for the reporter (their own mistake) and hub managers. Frappe
    keeps the payload in `Deleted Document`, so an accidental delete is
    still recoverable from the desk.
    """
    gate_read()
    row = frappe.db.get_value("Hub Ticket", name,
                              ["name", "title", "reported_by"], as_dict=True)
    if not row:
        frappe.throw(_("Ticket {0} was not found.").format(name))

    from task_hub.api.utils import is_manager
    if not (is_manager() or row.reported_by == frappe.session.user):
        frappe.throw(
            _("Only the person who reported this ticket, or a manager, can delete it."),
            frappe.PermissionError)

    # Free the dependents first: blocked_by is a Link, so Frappe would
    # otherwise refuse the delete — and the waiting tickets would be left
    # pointing at nothing.
    for dep in frappe.get_all("Hub Ticket", filters={"blocked_by": name},
                              fields=["name"]):
        doc = frappe.get_doc("Hub Ticket", dep.name)
        doc.blocked_by = None
        doc.append("activity", {
            "activity_on": now_datetime(),
            "actor": frappe.session.user,
            "action": "Dependency",
            "detail": _("Blocker {0} was deleted").format(name),
        })
        doc.save(ignore_permissions=True)

    # Notifications pointing at a ticket that no longer exists are dead links.
    frappe.db.delete("Hub Notification", {"ticket": name})

    frappe.delete_doc("Hub Ticket", name, ignore_permissions=True,
                      delete_permanently=False)
    frappe.db.commit()
    return {"deleted": name, "title": row.title}


@frappe.whitelist()
def my_tasks(limit=25, scope="all"):
    """Compact personal feed for the in-portal task panel.

    Inherently scoped to the caller (assignee or reporter), so it needs no
    visibility fragment. One round-trip: the rows plus the counts the
    badge shows.
    """
    gate_read()
    user = frappe.session.user
    limit = max(1, min(50, int(limit)))

    if scope == "assigned":
        who = "assigned_to = %(me)s"
    elif scope == "reported":
        who = "reported_by = %(me)s"
    else:
        who = "(assigned_to = %(me)s OR reported_by = %(me)s)"

    rows = frappe.db.sql(
        f"""SELECT name, title, status, priority, ticket_type, due_date,
                   sla_breached, workspace, stage, assigned_to, reported_by,
                   source_portal, modified
            FROM `tabHub Ticket`
            WHERE {who} AND status IN ('Open', 'In Progress', 'In Review')
            ORDER BY sla_breached DESC,
                     CASE priority WHEN 'Urgent' THEN 0 WHEN 'High' THEN 1
                                   WHEN 'Medium' THEN 2 ELSE 3 END,
                     COALESCE(due_date, '2999-12-31') ASC
            LIMIT %(limit)s""",
        {"me": user, "limit": limit}, as_dict=True,
    )
    counts = frappe.db.sql(
        """SELECT
             SUM(assigned_to = %(me)s) assigned_open,
             SUM(reported_by = %(me)s) reported_open,
             SUM(assigned_to = %(me)s AND sla_breached = 1) breached
           FROM `tabHub Ticket`
           WHERE (assigned_to = %(me)s OR reported_by = %(me)s)
             AND status IN ('Open', 'In Progress', 'In Review')""",
        {"me": user}, as_dict=True,
    )[0]
    return {
        "tasks": rows,
        "assigned_open": int(counts.assigned_open or 0),
        "reported_open": int(counts.reported_open or 0),
        "breached": int(counts.breached or 0),
    }
