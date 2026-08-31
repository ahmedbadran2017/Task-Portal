from . import __version__ as app_version  # noqa: F401

app_name = "task_hub"
app_title = "Task Hub"
app_publisher = "Justyol"
app_description = "Cross-department task & issue management for the Justyol portals"
app_email = "info@justyol.com"
app_license = "MIT"

# Website route rules — serve the Vue SPA for all /taskhub/* routes
website_route_rules = [
    {"from_route": "/taskhub/<path:app_path>", "to_route": "taskhub"},
    {"from_route": "/taskhub", "to_route": "taskhub"},
]

# Install / Migrate hooks
after_install = "task_hub.install.after_install"
after_migrate = [
    "task_hub.install._create_portal_roles",
    "task_hub.install._ensure_default_workspace",
]

# Hub Ticket lifecycle (SLA, activity log, status stamps) lives in the DocType
# controller class — task_hub/task_hub/doctype/hub_ticket/hub_ticket.py — so no
# doc_events wiring is needed here.

# Flag silently-overdue tickets — saves only refresh the breach flag on write.
# Automation (auto-tickets, SLA notifications, digest) is gated by settings.
scheduler_events = {
    "hourly": [
        "task_hub.task_hub.doctype.hub_ticket.hub_ticket.refresh_sla_breaches",
        "task_hub.automation.notify_sla_risks",
        "task_hub.task_hub.doctype.hub_automation_rule.hub_automation_rule.run_automation_rules",
    ],
    "daily": [
        "task_hub.automation.run_auto_rules",
        "task_hub.task_hub.doctype.hub_recurring_ticket.hub_recurring_ticket.run_recurring_tickets",
    ],
    "weekly": [
        "task_hub.automation.send_weekly_digest",
        "task_hub.api.notifications.purge_old_notifications",
        "task_hub.api.push.purge_dead_subscriptions",
    ],
    "monthly": [
        "task_hub.automation.send_monthly_scorecard",
    ],
}
