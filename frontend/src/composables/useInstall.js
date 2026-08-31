// "Install the app" prompt for people who reached the hub in a phone browser.
//
// Two very different paths hide behind one banner. Android/Chrome fires
// `beforeinstallprompt`, which we stash and replay on a tap — a real one-touch
// install. iOS fires nothing and exposes no install API at all, so the only
// honest thing to show an iPhone user is where the Share button is.
import { ref, computed } from "vue";
import { isIOS, isStandalone } from "./usePush";

const DISMISS_KEY = "th_install_snoozed";
const INSTALLED_KEY = "th_installed";
// Long enough that a "not now" isn't asked again the same week, short enough
// that someone who genuinely wants notifications is reminded.
const SNOOZE_DAYS = 14;

export const deferredPrompt = ref(null);
export const installed = ref(false);

function store(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private mode — the banner simply reappears next visit */
  }
}
function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

// Armed from main.js: the event can fire before any component has mounted.
export function armInstallCapture() {
  if (typeof window === "undefined") return;
  // Seed the reactive state from storage once, at boot.
  snoozedAt.value = Number(read(DISMISS_KEY) || 0);
  everInstalled.value = !!read(INSTALLED_KEY);
  window.addEventListener("beforeinstallprompt", (e) => {
    // Chrome shows its own mini-infobar unless we take the event over.
    e.preventDefault();
    deferredPrompt.value = e;
  });
  window.addEventListener("appinstalled", () => {
    installed.value = true;
    everInstalled.value = true;
    deferredPrompt.value = null;
    store(INSTALLED_KEY, "1");
  });
}

export function isPhone() {
  if (typeof window === "undefined") return false;
  // Coarse pointer + narrow viewport: a desktop user can't install to a home
  // screen in any useful sense, so never nag them.
  const coarse = window.matchMedia?.("(pointer: coarse)").matches;
  return !!coarse && window.innerWidth < 1024;
}

// Held in a ref, not read from localStorage inside the computed: a computed
// only re-evaluates when a REACTIVE dependency changes, so reading storage
// directly would cache the pre-dismissal answer for the rest of the session.
const snoozedAt = ref(0);
const everInstalled = ref(false);

function snoozed() {
  return !!snoozedAt.value && Date.now() - snoozedAt.value < SNOOZE_DAYS * 86400000;
}

export const canShowBanner = computed(() => {
  if (installed.value || everInstalled.value) return false;
  if (isStandalone()) return false;       // already running as the app
  if (!isPhone()) return false;           // desktop has nothing to install to
  if (snoozed()) return false;
  // Android: only once Chrome says the app is installable.
  // iOS: always, because there is no event to wait for.
  return isIOS() || !!deferredPrompt.value;
});

export function snooze() {
  snoozedAt.value = Date.now();
  store(DISMISS_KEY, String(snoozedAt.value));
}

export async function promptInstall() {
  const evt = deferredPrompt.value;
  if (!evt) return { ok: false, reason: "unavailable" };
  evt.prompt();
  const { outcome } = await evt.userChoice;
  deferredPrompt.value = null;   // the event is single-use
  if (outcome === "accepted") {
    installed.value = true;
    everInstalled.value = true;
    store(INSTALLED_KEY, "1");
    return { ok: true };
  }
  snooze();
  return { ok: false, reason: outcome };
}
