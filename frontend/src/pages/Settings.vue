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
          <label class="text-sm text-ink-700">
            New Items missing content → <b>Content</b> ticket
            <span class="block text-[11px] text-ink-400">scans items created in the last N days for missing image/description:</span>
          </label>
          <div class="flex items-center gap-2 shrink-0">
            <input v-model.number="form.item_content_days" type="number" min="1" class="input !w-20" :disabled="!canEdit" />
            <Toggle v-model="form.auto_item_content" :disabled="!canEdit" />
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

    <!-- language: personal, applies immediately, no save needed -->
    <div class="card p-6">
      <h3 class="text-sm font-bold text-ink-900 mb-1">{{ t("Language") }} / اللغة</h3>
      <p class="text-xs text-ink-400 mb-4">Personal preference — stored on this device.</p>
      <div class="inline-flex rounded-xl border border-ink-200 overflow-hidden">
        <button
          class="px-5 py-2 text-sm font-semibold transition"
          :class="locale === 'en' ? 'bg-brand-500 text-white' : 'bg-white text-ink-600 hover:bg-ink-50'"
          @click="setLocale('en')"
        >English</button>
        <button
          class="px-5 py-2 text-sm font-semibold transition"
          :class="locale === 'ar' ? 'bg-brand-500 text-white' : 'bg-white text-ink-600 hover:bg-ink-50'"
          @click="setLocale('ar')"
        >العربية</button>
      </div>
    </div>

    <!-- workspaces -->
    <div class="card p-6">
      <div class="flex items-center justify-between mb-1">
        <h3 class="text-sm font-bold text-ink-900">{{ t("Workspaces") }}</h3>
        <button v-if="canEdit" class="btn-outline !py-1.5 text-xs" @click="startNewWs">
          + {{ t("Add workspace") }}
        </button>
      </div>
      <p class="text-xs text-ink-400 mb-4">
        One board per team, each with its own stages. Members come from the linked
        ERPNext department; tickets keep feeding company-wide scorecards.
      </p>

      <!-- editor -->
      <div v-if="wsForm" class="border border-ink-200 rounded-xl p-4 mb-4 space-y-3 bg-ink-50/50">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Name *</label>
            <input v-model="wsForm.workspace_name" class="input" :disabled="!!wsForm.name" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="label">Icon</label>
              <input v-model="wsForm.icon" class="input" maxlength="4" />
            </div>
            <div>
              <label class="label">Color</label>
              <input v-model="wsForm.color" type="color" class="input !p-1 h-[38px]" />
            </div>
          </div>
          <div>
            <label class="label">{{ t("Members from department") }}</label>
            <select v-model="wsForm.department" class="input">
              <option value="">—</option>
              <option v-for="d in departments" :key="d.name" :value="d.name">
                {{ d.name }} ({{ d.employees }})
              </option>
            </select>
          </div>
          <div class="flex items-end pb-1">
            <label class="flex items-center gap-2.5 text-sm text-ink-700">
              <Toggle v-model="wsForm.use_sla" />
              {{ t("SLA applies") }}
            </label>
          </div>
        </div>

        <div>
          <label class="label">{{ t("Stages (board columns)") }}</label>
          <div class="space-y-2">
            <div v-for="(st, i) in wsForm.stages" :key="i" class="flex items-center gap-2">
              <input v-model="st.stage_name" class="input !py-1.5 flex-1" placeholder="Stage name" />
              <select v-model="st.maps_to" class="input !py-1.5 !w-36" :title="t('Counts as')">
                <option v-for="s in STATUSES" :key="s" :value="s">{{ t(s) }}</option>
              </select>
              <input v-model="st.color" type="color" class="w-9 h-9 rounded-lg border border-ink-200 p-0.5 bg-white" />
              <button class="text-ink-300 hover:text-rose-600" @click="wsForm.stages.splice(i, 1)">✕</button>
            </div>
          </div>
          <button class="btn-ghost !py-1 text-xs mt-2" @click="wsForm.stages.push({ stage_name: '', maps_to: 'In Progress', color: '#a16207' })">
            + {{ t("Stage") }}
          </button>
        </div>

        <div class="flex justify-end gap-2">
          <button class="btn-outline !py-1.5" @click="wsForm = null">{{ t("Cancel") }}</button>
          <button class="btn-primary !py-1.5" :disabled="savingWs" @click="saveWs">{{ t("Save") }}</button>
        </div>
      </div>

      <!-- list -->
      <div v-if="wsList.length" class="divide-y divide-ink-100">
        <div v-for="w in wsList" :key="w.name" class="py-3 flex items-center gap-3">
          <span class="w-8 h-8 rounded-lg grid place-items-center text-base shrink-0"
                :style="{ background: w.color + '22' }">{{ w.icon }}</span>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-medium text-ink-800 truncate">
              {{ w.name }}
              <span v-if="w.is_default" class="text-[10px] font-bold text-brand-600 ml-1">DEFAULT</span>
            </div>
            <div class="text-[11px] text-ink-400 truncate">
              {{ w.member_count }} {{ t("people") }} · {{ w.open_count }} {{ t("open") }}
              · {{ w.stages.map((s) => s.stage_name).join(" → ") }}
            </div>
          </div>
          <button v-if="canEdit" class="btn-ghost !px-2 !py-1 text-xs" @click="startEditWs(w)">✎</button>
          <button
            v-if="canEdit && !w.is_default"
            class="text-ink-300 hover:text-rose-600 text-sm"
            @click="removeWs(w)"
          >✕</button>
        </div>
      </div>
    </div>

    <!-- recurring tickets -->
    <div class="card p-6">
      <div class="flex items-center justify-between mb-1">
        <h3 class="text-sm font-bold text-ink-900">{{ t("Recurring tickets") }}</h3>
        <button v-if="canEdit" class="btn-outline !py-1.5 text-xs" @click="showRuleForm = !showRuleForm">
          + {{ t("Add rule") }}
        </button>
      </div>
      <p class="text-xs text-ink-400 mb-4">
        Tickets that open themselves on a schedule — weekly reports, monthly stock counts…
      </p>

      <div v-if="showRuleForm" class="border border-ink-200 rounded-xl p-4 mb-4 space-y-3 bg-ink-50/50">
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="label">{{ t("Title") }} *</label>
            <input v-model="ruleForm.title" class="input" />
          </div>
          <div>
            <label class="label">{{ t("Type") }}</label>
            <select v-model="ruleForm.ticket_type" class="input">
              <option v-for="tp in TYPES" :key="tp" :value="tp">{{ t(tp) }}</option>
            </select>
          </div>
          <div>
            <label class="label">{{ t("Priority") }}</label>
            <select v-model="ruleForm.priority" class="input">
              <option v-for="p in PRIORITIES" :key="p" :value="p">{{ t(p) }}</option>
            </select>
          </div>
          <div>
            <label class="label">Frequency</label>
            <select v-model="ruleForm.frequency" class="input">
              <option value="Daily">{{ t("Daily") }}</option>
              <option value="Weekly">{{ t("Weekly") }}</option>
              <option value="Monthly">{{ t("Monthly") }}</option>
            </select>
          </div>
          <div v-if="ruleForm.frequency === 'Weekly'">
            <label class="label">Weekday</label>
            <select v-model="ruleForm.weekday" class="input">
              <option v-for="d in WEEKDAYS" :key="d">{{ d }}</option>
            </select>
          </div>
          <div v-if="ruleForm.frequency === 'Monthly'">
            <label class="label">Day of month</label>
            <input v-model.number="ruleForm.day_of_month" type="number" min="1" max="28" class="input" />
          </div>
          <div class="col-span-2">
            <label class="label">{{ t("Assign To") }}</label>
            <UserPicker v-model="ruleForm.assigned_to" :users="users" />
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn-outline !py-1.5" @click="showRuleForm = false">{{ t("Cancel") }}</button>
          <button class="btn-primary !py-1.5" :disabled="!ruleForm.title.trim() || savingRule" @click="saveRule">
            {{ t("Save") }}
          </button>
        </div>
      </div>

      <div v-if="rules.length" class="divide-y divide-ink-100">
        <div v-for="r in rules" :key="r.name" class="py-3 flex items-center gap-3">
          <Toggle
            :model-value="r.active"
            :disabled="!canEdit"
            @update:model-value="toggleRule(r, $event)"
          />
          <div class="min-w-0 flex-1">
            <div class="text-sm font-medium text-ink-800 truncate">{{ r.title }}</div>
            <div class="text-[11px] text-ink-400">
              {{ t(r.frequency) }}
              <template v-if="r.frequency === 'Weekly'"> · {{ r.weekday }}</template>
              <template v-if="r.frequency === 'Monthly'"> · day {{ r.day_of_month }}</template>
              <template v-if="r.assigned_to"> · {{ r.assigned_to.split("@")[0] }}</template>
              <template v-if="r.last_run"> · last: {{ r.last_run }}</template>
            </div>
          </div>
          <button v-if="canEdit" class="text-ink-300 hover:text-rose-600 text-sm" @click="removeRule(r)">✕</button>
        </div>
      </div>
      <p v-else class="text-xs text-ink-400">No rules yet.</p>
    </div>

    <div v-if="canEdit" class="flex justify-end gap-2">
      <button class="btn-outline" :disabled="saving" @click="load">{{ t("Reset") }}</button>
      <button class="btn-primary" :disabled="saving" @click="save">
        {{ saving ? t("Saving…") : t("Save Settings") }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, h } from "vue";
import UserPicker from "@/components/UserPicker.vue";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";
import { useWorkspaces } from "@/composables/useWorkspaces";
import {
  TYPES, PRIORITIES, PRIORITY_META, getSettings, updateSettings, whoami,
  assignableUsers, listRecurringRules, saveRecurringRule, deleteRecurringRule,
} from "@/composables/useTickets";

const toast = useToast();
const { t, locale, setLocale } = useI18n();
const error = ref("");
const saving = ref(false);
const canEdit = ref(false);

// workspaces management
const STATUSES = ["Open", "In Progress", "In Review", "Resolved", "Closed", "Cancelled"];
const {
  workspaces: wsList, reload: reloadWs, saveWorkspace, deleteWorkspace, listDepartments,
} = useWorkspaces();
const departments = ref([]);
const wsForm = ref(null);
const savingWs = ref(false);

function startNewWs() {
  wsForm.value = {
    workspace_name: "",
    icon: "🗂️",
    color: "#d45d3e",
    department: "",
    use_sla: 1,
    stages: [
      { stage_name: "To Do", maps_to: "Open", color: "#3b82f6" },
      { stage_name: "Doing", maps_to: "In Progress", color: "#a16207" },
      { stage_name: "Review", maps_to: "In Review", color: "#7c3aed" },
      { stage_name: "Done", maps_to: "Resolved", color: "#059669" },
    ],
  };
}

function startEditWs(w) {
  wsForm.value = {
    name: w.name,
    workspace_name: w.name,
    icon: w.icon,
    color: w.color,
    department: w.department || "",
    use_sla: w.use_sla,
    stages: w.stages.map((s) => ({ ...s })),
  };
}

async function saveWs() {
  savingWs.value = true;
  try {
    await saveWorkspace(wsForm.value);
    wsForm.value = null;
    await reloadWs();
    toast.success("Workspace saved");
  } catch (e) {
    toast.error(e.message || "Could not save workspace");
  } finally {
    savingWs.value = false;
  }
}

async function removeWs(w) {
  if (!confirm(`Delete workspace "${w.name}"? Its tickets move to the default workspace.`)) return;
  try {
    await deleteWorkspace(w.name);
    await reloadWs();
    toast.success("Workspace deleted");
  } catch (e) {
    toast.error(e.message || "Could not delete workspace");
  }
}

// recurring rules
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const rules = ref([]);
const users = ref([]);
const showRuleForm = ref(false);
const savingRule = ref(false);
const ruleForm = reactive({
  title: "",
  ticket_type: "Task",
  priority: "Medium",
  frequency: "Weekly",
  weekday: "Monday",
  day_of_month: 1,
  assigned_to: "",
});

async function loadRules() {
  try {
    rules.value = await listRecurringRules();
  } catch {}
}

async function saveRule() {
  savingRule.value = true;
  try {
    await saveRecurringRule({ ...ruleForm, active: 1 });
    showRuleForm.value = false;
    Object.assign(ruleForm, { title: "", assigned_to: "" });
    await loadRules();
    toast.success("Rule saved");
  } catch (e) {
    toast.error(e.message || "Could not save rule");
  } finally {
    savingRule.value = false;
  }
}

async function toggleRule(r, val) {
  try {
    await saveRecurringRule({ name: r.name, active: val ? 1 : 0 });
    r.active = val ? 1 : 0;
  } catch (e) {
    toast.error(e.message || "Could not update rule");
  }
}

async function removeRule(r) {
  try {
    await deleteRecurringRule(r.name);
    rules.value = rules.value.filter((x) => x.name !== r.name);
  } catch (e) {
    toast.error(e.message || "Could not delete rule");
  }
}

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
  auto_item_content: 0,
  item_content_days: 7,
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
    loadRules();
    if (!users.value.length) assignableUsers("").then((u) => (users.value = u)).catch(() => {});
    if (!departments.value.length) listDepartments().then((d) => (departments.value = d)).catch(() => {});
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
