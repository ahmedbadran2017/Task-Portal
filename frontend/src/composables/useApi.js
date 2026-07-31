// Thin wrappers around Frappe's method API (cookie-auth + CSRF, JSON only).

export const COMPANY =
  (typeof window !== "undefined" && window.task_hub_company) || "Justyol Morocco";

export function getUserRoles() {
  return typeof window !== "undefined" && Array.isArray(window.user_roles)
    ? window.user_roles
    : [];
}

export function hasRole(...roles) {
  const have = new Set(getUserRoles());
  if (have.has("Administrator") || have.has("System Manager")) return true;
  return roles.some((r) => have.has(r));
}

export function currentUserId() {
  return (typeof window !== "undefined" && window.user_id) || "Guest";
}

// Mirrors MANAGER_ROLES in task_hub/api/utils.py — managers see the whole
// hub; everyone else only their own tickets. hasRole() already grants
// Administrator / System Manager.
export function isManager() {
  return hasRole(
    "Task Hub Admin", "Task Hub Manager",
    "Purchase Manager", "Accounts Manager", "Logistics Manager", "Stock Manager"
  );
}

function getCsrf() {
  if (typeof window !== "undefined" && window.csrf_token) return window.csrf_token;
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

export function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Server messages arrive as JSON-in-JSON and often carry HTML markup
// (<details>, <strong>, …) meant for Frappe's desk — strip it so error
// banners show clean text instead of raw tags.
function stripHtml(s) {
  return String(s)
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function parseServerMessages(raw) {
  if (!raw) return "";
  try {
    const arr = typeof raw === "string" ? JSON.parse(raw) : raw;
    if (!Array.isArray(arr)) return stripHtml(raw);
    return arr
      .map((m) => {
        if (m && typeof m === "object") return m.message || JSON.stringify(m);
        try {
          return JSON.parse(m).message || m;
        } catch {
          return m;
        }
      })
      .map(stripHtml)
      .join(" · ");
  } catch {
    return stripHtml(raw);
  }
}

export function cleanError(e) {
  return stripHtml(e?.message || e || "");
}

// GET a whitelisted method (read-only, no CSRF needed).
export async function getMethod(method, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  });
  const url = "/api/method/" + method + (qs.toString() ? "?" + qs.toString() : "");
  const resp = await fetch(url, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  let j = {};
  try {
    j = await resp.json();
  } catch {}
  if (!resp.ok || j.exc) {
    const msg = parseServerMessages(j._server_messages) || j.exc || "HTTP " + resp.status;
    throw new Error(msg);
  }
  return j.message;
}

// POST to a whitelisted method (handles CSRF + server-message parsing).
export async function callMethod(method, args = {}) {
  const resp = await fetch("/api/method/" + method, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": getCsrf(),
      Accept: "application/json",
    },
    body: JSON.stringify(args),
  });
  let j = {};
  try {
    j = await resp.json();
  } catch {}
  if (!resp.ok || j.exc) {
    const msg = parseServerMessages(j._server_messages) || j.exc || "HTTP " + resp.status;
    const err = new Error(msg);
    err.payload = j.message || j;
    err.status = resp.status;
    throw err;
  }
  return j.message;
}

// ---- formatting helpers -------------------------------------------------
// Dates and relative times follow the active UI language; the locale is read
// from storage rather than imported so this module stays dependency-free.
const INTL_LOCALES = { ar: "ar-EG", fr: "fr-FR", en: "en-GB" };

function activeLocale() {
  try {
    const l = localStorage.getItem("th_lang") ||
      (typeof window !== "undefined" && window.user_lang) || "en";
    return String(l).slice(0, 2);
  } catch {
    return "en";
  }
}

function intlLocale() {
  return INTL_LOCALES[activeLocale()] || "en-GB";
}

// Intl.RelativeTimeFormat handles plurals and word order per language, which
// hand-built "3 hours ago" strings never did.
export function relTime(value) {
  if (!value) return "";
  const d = new Date(String(value).replace(" ", "T"));
  if (isNaN(d.getTime())) return "";
  const diff = (Date.now() - d.getTime()) / 1000;
  const abs = Math.abs(diff);
  const sign = diff < 0 ? 1 : -1;
  let rtf;
  try {
    rtf = new Intl.RelativeTimeFormat(intlLocale(), { numeric: "auto" });
  } catch {
    rtf = new Intl.RelativeTimeFormat("en-GB", { numeric: "auto" });
  }
  if (abs < 60) return rtf.format(sign * Math.round(abs), "second");
  if (abs < 3600) return rtf.format(sign * Math.round(abs / 60), "minute");
  if (abs < 86400) return rtf.format(sign * Math.round(abs / 3600), "hour");
  if (abs < 2592000) return rtf.format(sign * Math.round(abs / 86400), "day");
  return d.toLocaleDateString(intlLocale(), { day: "2-digit", month: "short" });
}

export function fmtDate(value) {
  if (!value) return "—";
  const d = new Date(String(value).replace(" ", "T"));
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(intlLocale(),
    { day: "2-digit", month: "short", year: "numeric" });
}

export { activeLocale, intlLocale };
