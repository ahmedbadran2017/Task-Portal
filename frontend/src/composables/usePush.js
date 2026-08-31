// Phone notifications: service worker + Web Push subscription.
//
// The awkward part is iOS. Safari has supported Web Push since 16.4, but ONLY
// for a PWA the user has added to their Home Screen — from a normal Safari tab
// the APIs are simply absent. So the UI has to detect that case and teach the
// install step rather than showing a permission button that can never work.
import { ref, computed } from "vue";
import { callMethod, getMethod } from "./useApi";

const M = "task_hub.api.push";

export const supported = ref(
  typeof navigator !== "undefined" &&
    "serviceWorker" in navigator &&
    typeof window !== "undefined" &&
    "PushManager" in window &&
    "Notification" in window
);

export const permission = ref(
  typeof Notification !== "undefined" ? Notification.permission : "default"
);
export const subscribed = ref(false);
export const busy = ref(false);
export const serverReady = ref(false);

// Running as an installed app rather than a browser tab.
export function isStandalone() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

export function isIOS() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  // iPadOS 13+ reports itself as a Mac; the touch points give it away.
  return /iPad|iPhone|iPod/.test(ua) ||
    (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
}

// iOS can do push, but only once installed — the reason a button alone
// wouldn't be enough.
export const needsInstallFirst = computed(
  () => isIOS() && !isStandalone() && !supported.value
);

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

let registration = null;

async function register() {
  if (registration) return registration;
  // Scoped to /taskhub/ so the worker never intercepts the ERPNext desk.
  registration = await navigator.serviceWorker.register("/taskhub-sw.js", {
    scope: "/taskhub/",
  });
  // A freshly installed worker isn't usable until it activates; subscribing
  // against an installing worker throws.
  if (!registration.active) {
    await new Promise((resolve) => {
      const worker = registration.installing || registration.waiting;
      if (!worker) return resolve();
      worker.addEventListener("statechange", () => {
        if (worker.state === "activated") resolve();
      });
      setTimeout(resolve, 5000);
    });
  }
  return registration;
}

// Is this browser already subscribed, and is the server set up at all?
export async function refresh() {
  if (!supported.value) return;
  try {
    const { enabled } = await getMethod(`${M}.public_key`);
    serverReady.value = !!enabled;
    if (!enabled) return;
    const reg = await register();
    const sub = await reg.pushManager.getSubscription();
    subscribed.value = !!sub;
    permission.value = Notification.permission;
  } catch {
    serverReady.value = false;
  }
}

export async function enable() {
  if (!supported.value || busy.value) return { ok: false };
  busy.value = true;
  try {
    const { key, enabled } = await getMethod(`${M}.public_key`);
    if (!enabled || !key) {
      return { ok: false, reason: "not_configured" };
    }
    const result = await Notification.requestPermission();
    permission.value = result;
    if (result !== "granted") return { ok: false, reason: result };

    const reg = await register();
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(key),
      });
    }
    await callMethod(`${M}.subscribe`, { subscription: JSON.stringify(sub) });
    subscribed.value = true;
    return { ok: true };
  } catch (e) {
    return { ok: false, reason: e?.message || "failed" };
  } finally {
    busy.value = false;
  }
}

export async function disable() {
  if (busy.value) return;
  busy.value = true;
  try {
    const reg = await register();
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      await callMethod(`${M}.unsubscribe`, { endpoint: sub.endpoint });
      await sub.unsubscribe();
    } else {
      await callMethod(`${M}.unsubscribe`, {});
    }
    subscribed.value = false;
  } catch {
    /* leaving the row behind is harmless: a dead endpoint self-purges */
  } finally {
    busy.value = false;
  }
}

export function sendTest() {
  return callMethod(`${M}.send_test`);
}
export function getPreferences() {
  return getMethod(`${M}.get_preferences`);
}
export function savePreferences(prefs) {
  return callMethod(`${M}.save_preferences`, prefs);
}
export function myDevices() {
  return getMethod(`${M}.my_devices`);
}
export function forgetDevice(endpoint) {
  return callMethod(`${M}.unsubscribe`, { endpoint });
}
