<template>
  <div class="card p-6">
    <h3 class="text-sm font-bold text-ink-900 mb-1">{{ t("Phone notifications") }}</h3>
    <p class="text-xs text-ink-400 mb-5">
      {{ t("Get a buzz on your phone the moment work needs you.") }}
    </p>

    <!-- iOS in a Safari tab: the APIs don't exist there at all, so a permission
         button would be a dead end. Teach the install instead. -->
    <div v-if="needsInstallFirst" class="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
      <div class="flex items-start gap-2.5">
        <NavIcon name="phone" :size="16" class="text-amber-700 mt-0.5 shrink-0" />
        <div class="min-w-0">
          <p class="text-sm font-semibold text-ink-800">
            {{ t("Add Task Hub to your Home Screen first") }}
          </p>
          <p class="text-xs text-ink-600 mt-1">
            {{ t("On iPhone, notifications only work once the app is installed.") }}
          </p>
          <ol class="text-xs text-ink-700 mt-2.5 space-y-1 list-decimal ms-4">
            <li>{{ t("Tap the Share button in Safari") }}</li>
            <li>{{ t("Choose “Add to Home Screen”") }}</li>
            <li>{{ t("Open Task Hub from the new icon, then come back here") }}</li>
          </ol>
        </div>
      </div>
    </div>

    <div v-else-if="!supported" class="text-sm text-ink-500">
      {{ t("This browser can't do notifications. Try Chrome on Android, or install the app on iPhone.") }}
    </div>

    <div v-else-if="!serverReady" class="text-sm text-ink-500">
      {{ t("Push isn't set up on the server yet — an administrator needs to add the keys.") }}
    </div>

    <div v-else-if="permission === 'denied'" class="text-sm text-ink-500">
      {{ t("Notifications are blocked for this site. Turn them back on in your browser or phone settings, then reload.") }}
    </div>

    <div v-else class="space-y-4">
      <div class="flex items-center justify-between gap-4">
        <label class="text-sm text-ink-700">
          {{ t("Notifications on this device") }}
          <span class="block text-[11px] text-ink-400">{{ deviceHint }}</span>
        </label>
        <Toggle :model-value="subscribed" :disabled="busy" @update:model-value="onToggle" />
      </div>

      <template v-if="subscribed">
        <div class="border-t border-ink-100 pt-4">
          <p class="label">{{ t("Buzz my phone when") }}</p>
          <div class="grid sm:grid-cols-2 gap-x-6 gap-y-2.5 mt-1">
            <label v-for="p in PREFS" :key="p.key"
                   class="flex items-center justify-between gap-3 text-sm text-ink-700">
              <span>{{ t(p.label) }}</span>
              <Toggle v-model="prefs[p.key]" @update:model-value="persist" />
            </label>
          </div>
        </div>

        <div class="border-t border-ink-100 pt-4">
          <p class="label">{{ t("Quiet hours") }}</p>
          <p class="text-[11px] text-ink-400 mb-2">
            {{ t("The phone stays silent; the bell and email still work.") }}
          </p>
          <div class="flex items-center gap-2">
            <input v-model="prefs.quiet_from" type="time" class="input !w-32" @change="persist" />
            <span class="text-xs text-ink-400">→</span>
            <input v-model="prefs.quiet_to" type="time" class="input !w-32" @change="persist" />
            <button v-if="prefs.quiet_from || prefs.quiet_to"
                    class="btn-ghost !px-2 !py-1 text-xs" @click="clearQuiet">
              {{ t("Clear") }}
            </button>
          </div>
        </div>

        <div class="border-t border-ink-100 pt-4 flex items-center justify-between gap-3">
          <span class="text-xs text-ink-400">
            {{ devices.length }} {{ t("device(s) registered") }}
          </span>
          <button class="btn-outline !py-1.5 text-xs" :disabled="testing" @click="onTest">
            <NavIcon name="bell" :size="12" /> {{ testing ? t("Sending…") : t("Send a test") }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import NavIcon from "./NavIcon.vue";
import Toggle from "./Toggle.vue";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import {
  supported, permission, subscribed, busy, serverReady, needsInstallFirst,
  refresh, enable, disable, sendTest, getPreferences, savePreferences, myDevices,
} from "@/composables/usePush";

const { t } = useI18n();
const toast = useToast();

const PREFS = [
  { key: "on_assigned", label: "Work is assigned to me" },
  { key: "on_mention", label: "Someone mentions me" },
  { key: "on_sla", label: "A deadline is close or missed" },
  { key: "on_comment", label: "Someone comments on my ticket" },
  { key: "on_resolved", label: "My ticket is resolved" },
  { key: "on_status", label: "A ticket I watch changes status" },
];

const prefs = reactive({
  on_assigned: 1, on_mention: 1, on_sla: 1,
  on_comment: 1, on_resolved: 1, on_status: 0,
  quiet_from: "", quiet_to: "",
});
const devices = ref([]);
const testing = ref(false);

const deviceHint = computed(() =>
  subscribed.value ? t("This device will buzz.") : t("Off — nothing reaches this phone.")
);

async function loadDevices() {
  try {
    devices.value = await myDevices();
  } catch {
    devices.value = [];
  }
}

async function onToggle(want) {
  if (want) {
    const res = await enable();
    if (!res.ok) {
      toast.error(
        res.reason === "denied"
          ? t("You blocked notifications — allow them in your browser settings.")
          : t("Could not turn on notifications.")
      );
      return;
    }
    toast.success(t("Notifications on."));
    Object.assign(prefs, await getPreferences());
  } else {
    await disable();
    toast.success(t("Notifications off for this device."));
  }
  loadDevices();
}

async function persist() {
  try {
    Object.assign(prefs, await savePreferences({ ...prefs }));
  } catch (e) {
    toast.error(e.message || "Could not save");
  }
}

function clearQuiet() {
  prefs.quiet_from = "";
  prefs.quiet_to = "";
  persist();
}

async function onTest() {
  testing.value = true;
  try {
    const { sent } = await sendTest();
    if (sent > 0) toast.success(t("Sent to {0} device(s) — check your phone.", sent));
    else toast.error(t("No device received it. Try turning notifications off and on again."));
  } catch (e) {
    toast.error(e.message || "Test failed");
  } finally {
    testing.value = false;
  }
}

onMounted(async () => {
  await refresh();
  if (subscribed.value) {
    try {
      Object.assign(prefs, await getPreferences());
    } catch {}
    loadDevices();
  }
});
</script>
