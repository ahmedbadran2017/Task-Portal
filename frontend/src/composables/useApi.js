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
// hub; everyone else only their own tickets plus any board they lead.
// hasRole() already grants Administrator / System Manager.
//
// ERPNext's Purchase/Accounts/Logistics/Stock Manager roles were dropped from
// both sides: they are day-to-day operational grants, not "runs the Task Hub".
// Supervising a team is said per board via its leads, which the server checks —
// this flag stays a pure whole-hub test.
export function isManager() {
  return hasRole("Task Hub Admin", "Task Hub Manager");
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
// Arabic pins the Latin numbering system: the default ar-EG digits (٣١) clash
// with every other number in the UI, which renders Western.
const INTL_LOCALES = { ar: "ar-EG-u-nu-latn", fr: "fr-FR", en: "en-GB" };

// Frappe stores datetimes as naive strings in the SITE timezone. `new Date()`
// would read them as browser-local, so a Morocco browser (UTC+1) against an
// Istanbul site (UTC+3) shifted every timestamp by two hours — enough to make
// "3 hours ago" read as "in an hour".
function siteTimeZone() {
  return (typeof window !== "undefined" && window.task_hub_tz) || "";
}

// How far `timeZone` sits from UTC at the given instant (DST included).
function zoneOffsetMs(instant, timeZone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone, hour12: false,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  })
    .formatToParts(instant)
    .reduce((acc, p) => ((acc[p.type] = p.value), acc), {});
  const asUTC = Date.UTC(
    +parts.year, +parts.month - 1, +parts.day,
    +parts.hour % 24, +parts.minute, +parts.second
  );
  return asUTC - instant.getTime();
}

// Parse a server value into a real instant, honouring the site timezone.
export function parseServerDate(value) {
  if (!value) return null;
  const raw = String(value).trim();
  const m = raw.match(
    /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/
  );
  if (!m) return null;
  const [, y, mo, d, hh, mi, ss] = m;
  // Date-only values (due_date) carry no time, so no zone conversion applies.
  if (hh === undefined) return new Date(+y, +mo - 1, +d);

  const wallClock = Date.UTC(+y, +mo - 1, +d, +hh, +mi, +(ss || 0));
  const tz = siteTimeZone();
  if (!tz) return new Date(raw.replace(" ", "T"));
  try {
    // Resolve twice so a DST boundary lands on the right side.
    let instant = wallClock - zoneOffsetMs(new Date(wallClock), tz);
    instant = wallClock - zoneOffsetMs(new Date(instant), tz);
    return new Date(instant);
  } catch {
    return new Date(raw.replace(" ", "T"));
  }
}

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
  const d = parseServerDate(value);
  if (!d || isNaN(d.getTime())) return "";
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

// Elapsed durations read as answers ("1d 7h"), not decimals ("31.5"). Intl
// supplies the unit words, so Arabic and French don't need their own table.
export function fmtDuration(hours) {
  if (hours == null || hours === "") return "";
  const h = Number(hours);
  if (!isFinite(h) || h < 0) return "";
  const unit = (value, u) => {
    try {
      return new Intl.NumberFormat(intlLocale(), {
        style: "unit", unit: u, unitDisplay: "narrow", maximumFractionDigits: 0,
      }).format(value);
    } catch {
      return `${value}${u[0]}`;
    }
  };
  // Below an hour, minutes; a sub-hour ticket shown as "0h" reads as a bug.
  if (h < 1) return unit(Math.max(1, Math.round(h * 60)), "minute");
  // Round to hours FIRST, so 23.6h becomes "1d" rather than the "24h" that
  // sits awkwardly beside it in a sorted column.
  const totalH = Math.round(h);
  if (totalH < 24) return unit(totalH, "hour");
  const days = Math.floor(totalH / 24);
  const rest = totalH - days * 24;
  return rest ? `${unit(days, "day")} ${unit(rest, "hour")}` : unit(days, "day");
}

export function fmtDate(value) {
  if (!value) return "—";
  const d = parseServerDate(value);
  if (!d || isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(intlLocale(),
    { day: "2-digit", month: "short", year: "numeric" });
}

export { activeLocale, intlLocale };
