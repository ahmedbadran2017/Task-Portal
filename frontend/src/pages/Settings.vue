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
          <label class="label">Who can be assigned tickets</label>
          <select v-model="form.assignee_scope" class="input" :disabled="!canEdit">
            <option>Employees only</option>
            <option>Task Hub members</option>
            <option>All system users</option>
          </select>
          <p class="text-[11px] text-ink-400 mt-1.5">
            "Employees only" keeps supplier/customer logins and test accounts out
            of the assignee picker.
          </p>
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

    <div class="card p-6">
      <h3 class="text-sm font-bold text-ink-900 mb-1">Auto-tickets</h3>
      <p class="text-xs text-ink-400 mb-5">
        Daily rules that open tickets from live ERP data. Off by default — enable
        deliberately once the hub is in daily use.
      </p>
      <div class="space-y-4">
        <div class="flex items-center justify-between gap-4">
          <label class="text-sm text-ink-700">
            Overdue Sales Invoices → <b>Accounting</b> ticket
            <span class="block text-[11px] text-ink-400">when unpaid this many days past due:</span>
          </label>
          <div class="flex items-center gap-2 shrink-0">
            <input v-model.number="form.overdue_invoice_days" type="number" min="1" class="input !w-20" :disabled="!canEdit" />
            <Toggle v-model="form.auto_overdue_invoices" :disabled="!canEdit" />
          </div>
        </div>
        <div class="flex items-center justify-between gap-4">
          <label class="text-sm text-ink-700">
            Stuck Sales Orders → <b>Logistics</b> ticket
            <span class="block text-[11px] text-ink-400">when undelivered this many days after order date:</span>
          </label>
          <div class="flex items-center gap-2 shrink-0">
            <input v-model.number="form.stuck_order_days" type="number" min="1" class="input !w-20" :disabled="!canEdit" />
            <Toggle v-model="form.auto_stuck_orders" :disabled="!canEdit" />
          </div>
        </div>
        <div class="flex items-center justify-between gap-4">
          <label class="text-sm text-ink-700">Max auto-tickets per run</label>
          <input v-model.number="form.max_auto_tickets_per_run" type="number" min="1" max="200" class="input !w-20" :disabled="!canEdit" />
        </div>
      </div>
    </div>

    <div class="card p-6">
      <h3 class="text-sm font-bold text-ink-900 mb-5">Notifications</h3>
      <div class="space-y-4">
        <div class="flex items-center justify-between gap-4">
          <label class="text-sm text-ink-700">Email the assignee when a ticket is assigned</label>
          <Toggle v-model="form.notify_on_assignment" :disabled="!canEdit" />
        </div>
        <div class="flex items-center justify-between gap-4">
          <label class="text-sm text-ink-700">
            SLA warnings to assignees + escalate breaches to managers
            <span class="block text-[11px] text-ink-400">warning fires in the final quarter of the SLA budget</span>
          </label>
          <Toggle v-model="form.notify_sla" :disabled="!canEdit" />
        </div>
        <div class="flex items-center justify-between gap-4">
          <label class="text-sm text-ink-700">Weekly digest (per-portal summary)</label>
          <Toggle v-model="form.weekly_digest" :disabled="!canEdit" />
        </div>
        <div>
          <label class="label">Digest / escalation recipients</label>
          <textarea
            v-model="form.digest_recipients"
            rows="2"
            class="input resize-none"
            placeholder="Comma-separated emails — empty sends to every Task Hub manager"
            :disabled="!canEdit"
          />
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
import { reactive, ref, onMounted, h } from "vue";
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
  auto_overdue_invoices: 0,
  overdue_invoice_days: 3,
  auto_stuck_orders: 0,
  stuck_order_days: 3,
  max_auto_tickets_per_run: 20,
  notify_on_assignment: 1,
  notify_sla: 1,
  weekly_digest: 0,
  digest_recipients: "",
  assignee_scope: "Employees only",
});

// Minimal styled switch — checkbox semantics, house colors.
const Toggle = {
  props: { modelValue: [Number, Boolean], disabled: Boolean },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () =>
      h(
        "button",
        {
          type: "button",
          class: [
            "relative w-10 h-6 rounded-full transition-colors shrink-0",
            props.modelValue ? "bg-brand-500" : "bg-ink-200",
            props.disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
          ],
          onClick: () => !props.disabled && emit("update:modelValue", props.modelValue ? 0 : 1),
        },
        [
          h("span", {
            class: "absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all",
            style: { left: props.modelValue ? "18px" : "2px" },
          }),
        ]
      );
  },
};

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
