# Task Hub

Cross-department task & issue management for the Justyol portals.

Task Hub is a Frappe app that installs on the **same ERPNext site** as the
Supplier, Accounting, Logistics, and Purchasing portals. Any portal can raise a
task/problem/request through one API call; everything lands in a single Kanban +
list + dashboard surface at **`/taskhub`**, with SLA tracking, assignment, and a
full activity log per ticket.

Same stack as every other portal: **Frappe** backend + **Vue 3 / Vite / Tailwind**
single-bundle SPA. No new database, no separate login — it reuses ERPNext users,
roles, and departments.

---

## Architecture

```
task_hub/                     Frappe app
├── hooks.py                  routes /taskhub/* → SPA, install/migrate hooks
├── install.py                creates the 4 Task Hub roles
├── api/
│   ├── auth.py               whoami, assignable_users
│   ├── tickets.py            create_ticket (universal entrypoint) + CRUD/workflow
│   ├── dashboard.py          get_summary (counts, breaches, breakdowns)
│   └── utils.py              role gates, portal→department map
├── task_hub/doctype/
│   ├── hub_ticket/           main DocType (SLA + activity lifecycle in controller)
│   ├── hub_ticket_comment/   child table
│   └── hub_ticket_activity/  child table (immutable audit trail)
├── www/taskhub.{py,html}     Jinja SPA shell (login gate + shell globals)
└── public/task_hub.bundle.*  built SPA (produced by frontend/)

frontend/                     Vue SPA source (build → task_hub/public/)
├── src/pages/                Dashboard, Board (Kanban), TicketList
├── src/components/           TicketCard, CreateTicketModal, TicketDrawer, …
└── src/composables/          useApi, useTickets (API surface), useUi, useToast
```

### The `Hub Ticket` model

| Field | Purpose |
|---|---|
| `title`, `description`, `ticket_type` | Task / Problem / Request |
| `source_portal`, `department` | where it came from; department auto-derived |
| `priority`, `status` | Urgent…Low · Open → In Progress → In Review → Resolved → Closed |
| `reported_by`, `assigned_to`, `due_date` | ownership |
| `sla_deadline`, `sla_breached`, `resolved_on` | computed from priority, stamped automatically |
| `linked_doctype`/`linked_name`/`linked_label`/`linked_url` | deep-link back to the real record in its portal |
| `comments`, `activity` | discussion + immutable audit trail |

**SLA budgets** (priority → hours): Urgent 4h · High 24h · Medium 72h · Low 168h.

### Roles

`Task Hub Admin` (all depts) · `Task Hub Manager` (triage/assign) ·
`Task Hub Agent` (work tickets) · `Task Hub User` (report + see own).
Existing `Purchase/Accounts/Logistics/Stock Manager` roles get manager-level
visibility automatically.

---

## Install (on the bench)

```bash
cd ~/frappe-bench
bench get-app task_hub git@github.com:ahmedbadran2017/task_hub.git
bench --site admin.justyol.com install-app task_hub
bench --site admin.justyol.com migrate
bench build --app task_hub
```

Then open **`https://admin.justyol.com/taskhub`**.

## Local development

```bash
cd frontend
cp .env.local.example .env.local   # optional: point FRAPPE_DEV_URL at a bench
npm install
npm run dev                        # http://localhost:8083, proxies API to admin.justyol.com
```

Ship a new build with `./deploy.sh "message"` (builds the bundle, commits, pushes).

---

## Integrating a portal (Phase 2)

Every portal already ships the same `callMethod` helper in
`frontend/src/composables/useApi.js`. Raising a ticket from **any** portal is one
call — no new dependency, same session/CSRF:

```js
// e.g. in Purchasing, from a "Report Problem" button on a Selection row
import { callMethod } from "@/composables/useApi";

await callMethod("task_hub.api.tickets.create_ticket", {
  payload: JSON.stringify({
    title: `Supplier didn't reply on ${sel.title}`,
    ticket_type: "Problem",
    priority: "High",
    source_portal: "Purchasing",
    description: "No quote after 5 days.",
    linked_doctype: "Selection",
    linked_name: sel.name,
    linked_label: sel.name,
    linked_url: `/purchasing/selections/${sel.name}`,
  }),
});
```

Server-side (e.g. an automation that opens a ticket when an SLA is missed):

```python
import frappe

frappe.get_doc({
    "doctype": "Hub Ticket",
    "title": f"Order {so.name} past dispatch SLA",
    "ticket_type": "Problem",
    "priority": "Urgent",
    "source_portal": "Logistics",
    "linked_doctype": "Sales Order",
    "linked_name": so.name,
    "linked_label": so.name,
    "linked_url": f"/logistics/orders/{so.name}",
}).insert(ignore_permissions=True)
```

A drop-in **"Report Problem"** button component for the portals lands in Phase 2.

---

## Roadmap

- **Phase 1 (this repo):** app + `Hub Ticket` model + API + Hub SPA (dashboard,
  Kanban board, list, ticket drawer, SLA, comments, activity). ✅
- **Phase 2:** shared "Report Problem / New Task" button embedded in each portal,
  auto-linking to the record in view.
- **Phase 3:** rule-based auto-tickets (SLA breaches, overdue invoices, low stock),
  email/notification escalation, and a CEO roll-up view.
