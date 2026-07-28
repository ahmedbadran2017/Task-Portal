// Domain wrappers over the Task Hub API + shared UI constants.
import { callMethod, getMethod } from "./useApi";

const M = "task_hub.api";

export const PORTALS = ["Supplier", "Accounting", "Logistics", "Purchasing", "Other"];
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
  Other: { color: "#64748b", label: "Other" },
};

export function getSummary() {
  return getMethod(`${M}.dashboard.get_summary`);
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

export function assignableUsers(search = "") {
  return getMethod(`${M}.auth.assignable_users`, { search });
}

export function whoami() {
  return getMethod(`${M}.auth.whoami`);
}
