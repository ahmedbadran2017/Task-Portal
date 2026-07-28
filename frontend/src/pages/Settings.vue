<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div v-if="!canEdit" class="card p-4 text-sm text-ink-500 bg-ink-50">
      Settings are read-only for your role — ask a Task Hub manager to change them.
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <div class="card p-6">
      <h3 class="text-sm font-bold text-ink-900 mb-1">SLA budgets</h3>
      <p class="text-xs text-ink-400 mb-5">
        Hours a ticket may stay open per priority before it counts as breached.
        Changing these only affects tickets created or re-prioritised afterwards.
      </p>
      <div class="grid grid-cols-2 gap-4">
        <div v-for="f in slaFields" :key="f.key">
          <label class="label flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full" :style="{ background: f.color }" />
            {{ f.label }}
          </label>
          <div class="relative">
            <input
              v-model.number="form[f.key]"
              type="number"
              min="1"
              class="input pr-14"
              :disabled="!canEdit"
            />
            <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ink-400">hours</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card p-6">
      <h3 class="text-sm font-bold text-ink-900 mb-5">Defaults & behaviour</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label">Default type</label>
          <select v-model="form.default_ticket_type" class="input" :disabled="!canEdit">
            <option v-for="t in TYPES" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
        <div>
          <label class="label">Default priority</label>
          <select v-model="form.default_priority" class="input" :disabled="!canEdit">
            <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="col-span-2">
          <label class="label">Auto-refresh (seconds, 0 = off)</label>
          <input
            v-model.number="form.auto_refresh_seconds"
            type="number"
            min="0"
            max="3600"
            class="input"
            :disabled="!canEdit"
          />
          <p class="text-[11px] text-ink-400 mt-1.5">
            How often the dashboard and board re-fetch in the background.
          </p>
        </div>
      </div>
    </div>

    <div v-if="canEdit" class="flex justify-end gap-2">
      <button class="btn-outline" :disabled="saving" @click="load">Reset</button>
      <button class="btn-primary" :disabled="saving" @click="save">
        {{ saving ? "Saving…" : "Save Settings" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { useToast } from "@/composables/useToast";
import { TYPES, PRIORITIES, PRIORITY_META, getSettings, updateSettings, whoami } from "@/composables/useTickets";

const toast = useToast();
const error = ref("");
const saving = ref(false);
const canEdit = ref(false);

const form = reactive({
  sla_urgent_hours: 4,
  sla_high_hours: 24,
  sla_medium_hours: 72,
  sla_low_hours: 168,
  default_ticket_type: "Task",
  default_priority: "Medium",
  auto_refresh_seconds: 60,
});

const slaFields = [
  { key: "sla_urgent_hours", label: "Urgent", color: PRIORITY_META.Urgent.color },
  { key: "sla_high_hours", label: "High", color: PRIORITY_META.High.color },
  { key: "sla_medium_hours", label: "Medium", color: PRIORITY_META.Medium.color },
  { key: "sla_low_hours", label: "Low", color: PRIORITY_META.Low.color },
];

async function load() {
  error.value = "";
  try {
    const [s, me] = await Promise.all([getSettings(), whoami()]);
    Object.assign(form, s);
    canEdit.value = !!me.is_manager;
  } catch (e) {
    error.value = e.message || "Could not load settings";
  }
}

async function save() {
  saving.value = true;
  try {
    const s = await updateSettings({ ...form });
    Object.assign(form, s);
    toast.success("Settings saved");
  } catch (e) {
    toast.error(e.message || "Could not save settings");
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>
