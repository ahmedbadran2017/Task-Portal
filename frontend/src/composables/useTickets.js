// Domain wrappers over the Task Hub API + shared UI constants.
import { callMethod, getMethod, parseServerMessages } from "./useApi";

const M = "task_hub.api";

export const PORTALS = ["Supplier", "Accounting", "Logistics", "Purchasing", "JoyAgent", "Website", "Mobile App", "Other"];
export const TYPES = ["Task", "Problem", "Request"];
export const PRIORITIES = ["Urgent", "High", "Medium", "Low"];
export const STATUSES = ["Open", "In Progress", "In Review", "Resolved", "Closed", "Cancelled"];

// The columns shown on the Kanban board (terminal states live in the list view).
export const BOARD_COLUMNS = ["Open", "In Progress", "In Review", "Resolved"];

export const PRIORITY_META = {
  Urgent: { color: "#e11d48", bg: "#fff1f2", ring: "#fecdd3", label: "Urgent" },
  High: { color: "#ea580c", bg: "#fff7ed", ring: "#fed7aa", label: "High" },
  Medium: { color: "#0891b2", bg: "#ecfeff", ring: "#a5f3fc", label: "Medium" },
  Low: { color: "#64748b", bg: "#f8fafc", ring: "#e2e8f0", label: "Low" },
};

export const STATUS_META = {
  Open: { color: "#3b82f6", bg: "#eff6ff", label: "Open" },
  "In Progress": { color: "#a16207", bg: "#fefce8", label: "In Progress" },
  "In Review": { color: "#7c3aed", bg: "#f5f3ff", label: "In Review" },
  Resolved: { color: "#059669", bg: "#ecfdf5", label: "Resolved" },
  Closed: { color: "#475569", bg: "#f1f5f9", label: "Closed" },
  Cancelled: { color: "#9f1239", bg: "#fff1f2", label: "Cancelled" },
};

export const PORTAL_META = {
  Supplier: { color: "#7c3aed", label: "Supplier" },
  Accounting: { color: "#059669", label: "Accounting" },
  Logistics: { color: "#2563eb", label: "Logistics" },
  Purchasing: { color: "#d97706", label: "Purchasing" },
  JoyAgent: { color: "#0d9488", label: "JoyAgent" },
  Website: { color: "#db2777", label: "Website" },
  "Mobile App": { color: "#4f46e5", label: "Mobile App" },
  Other: { color: "#64748b", label: "Other" },
};

export function getSummary() {
  return getMethod(`${M}.dashboard.get_summary`);
}

export function getTrends(weeks = 8) {
  return getMethod(`${M}.dashboard.get_trends`, { weeks });
}

export function listTickets(params = {}) {
  return getMethod(`${M}.tickets.list_tickets`, params);
}

export function getTicket(name) {
  return getMethod(`${M}.tickets.get_ticket`, { name });
}

export function createTicket(payload) {
  return callMethod(`${M}.tickets.create_ticket`, { payload: JSON.stringify(payload) });
}

export function updateStatus(name, status) {
  return callMethod(`${M}.tickets.update_status`, { name, status });
}

export function assignTicket(name, assigned_to) {
  return callMethod(`${M}.tickets.assign_ticket`, { name, assigned_to });
}

export function setPriority(name, priority) {
  return callMethod(`${M}.tickets.set_priority`, { name, priority });
}

export function addComment(name, message) {
  return callMethod(`${M}.tickets.add_comment`, { name, message });
}

export async function uploadAttachment(name, file) {
  const form = new FormData();
  form.append("file", file, file.name);
  const csrf =
    (typeof window !== "undefined" && window.csrf_token) ||
    (document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/) || [])[1] ||
    "";
  const resp = await fetch(
    `/api/method/${M}.tickets.upload_attachment?name=${encodeURIComponent(name)}`,
    {
      method: "POST",
      credentials: "include",
      headers: { "X-Frappe-CSRF-Token": decodeURIComponent(csrf) },
      body: form,
    }
  );
  let j = {};
  try {
    j = await resp.json();
  } catch {}
  if (!resp.ok || j.exc) {
    throw new Error(parseServerMessages(j._server_messages) || j.exc || "HTTP " + resp.status);
  }
  return j.message;
}

export function deleteAttachment(name, fileId) {
  return callMethod(`${M}.tickets.delete_attachment`, { name, file_id: fileId });
}

export function updateTicket(name, fields) {
  return callMethod(`${M}.tickets.update_ticket`, { name, ...fields });
}

export function watchTicket(name, watch) {
  return callMethod(`${M}.tickets.watch_ticket`, { name, watch: watch ? 1 : 0 });
}

export function checklistAdd(name, item) {
  return callMethod(`${M}.tickets.checklist_add`, { name, item });
}

export function checklistToggle(name, row) {
  return callMethod(`${M}.tickets.checklist_toggle`, { name, row });
}

export function checklistRemove(name, row) {
  return callMethod(`${M}.tickets.checklist_remove`, { name, row });
}

export function listRecurringRules() {
  return getMethod(`${M}.recurring.list_rules`);
}

export function saveRecurringRule(rule) {
  return callMethod(`${M}.recurring.save_rule`, rule);
}

export function deleteRecurringRule(name) {
  return callMethod(`${M}.recurring.delete_rule`, { name });
}

export function isImage(fileUrl) {
  return /\.(png|jpe?g|gif|webp|svg|heic)$/i.test(fileUrl || "");
}

export function fmtSize(bytes) {
  const n = Number(bytes) || 0;
  if (n < 1024) return n + " B";
  if (n < 1048576) return (n / 1024).toFixed(0) + " KB";
  return (n / 1048576).toFixed(1) + " MB";
}

export function assignableUsers(search = "") {
  return getMethod(`${M}.auth.assignable_users`, { search });
}

export function myNotifications(limit = 25) {
  return getMethod(`${M}.notifications.my_notifications`, { limit });
}

export function markSeen(name = "") {
  return callMethod(`${M}.notifications.mark_seen`, name ? { name } : {});
}

export const NOTIF_META = {
  assigned: { icon: "👤", color: "#d45d3e" },
  comment: { icon: "💬", color: "#2563eb" },
  mention: { icon: "@", color: "#7c3aed" },
  resolved: { icon: "✓", color: "#059669" },
  sla_warning: { icon: "⏳", color: "#d97706" },
  sla_breach: { icon: "⏰", color: "#e11d48" },
};

export function whoami() {
  return getMethod(`${M}.auth.whoami`);
}

export function polishDescription(text) {
  return callMethod(`${M}.ai.polish_description`, { text });
}

export function getWorkspaceScorecard(days = 30) {
  return getMethod(`${M}.scorecards.workspace_scorecard`, { days });
}

export function listTemplates(workspace = "") {
  return getMethod(`${M}.templates.list_templates`, { workspace });
}

export function saveTemplate(tpl) {
  return callMethod(`${M}.templates.save_template`, {
    ...tpl,
    checklist: tpl.checklist ? JSON.stringify(tpl.checklist) : undefined,
  });
}

export function deleteTemplate(name) {
  return callMethod(`${M}.templates.delete_template`, { name });
}

export function createFromTemplate(args) {
  return callMethod(`${M}.templates.create_from_template`, args);
}

export function getDepartmentScorecard(days = 30) {
  return getMethod(`${M}.scorecards.department_scorecard`, { days });
}

export function getEmployeeScorecard(days = 30, department = "", workspace = "") {
  return getMethod(`${M}.scorecards.employee_scorecard`, { days, department, workspace });
}

export function getSettings() {
  return getMethod(`${M}.settings.get_settings`);
}

export function updateSettings(payload) {
  return callMethod(`${M}.settings.update_settings`, payload);
}
