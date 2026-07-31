<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <p class="text-sm text-ink-500">{{ t("Live pulse from ERPNext + Task Hub health — refreshes every minute.") }}</p>
      <button class="btn-outline !py-1.5 text-xs" :disabled="loading" @click="load">
        <NavIcon name="refresh" :size="13" /> {{ t("Refresh") }}
      </button>
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">{{ error }}</div>

    <!-- ERP pulse -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <KpiTile
        icon="board" :label="t('Orders today')" :value="d.orders_today?.n"
        :sub="money(d.orders_today?.total)" tone="#d45d3e" tint="#fdf1ed"
      />
      <KpiTile
        icon="send" :label="t('Deliveries today')" :value="d.deliveries_today?.n"
        :sub="t('last 7 days: {0} orders', d.orders_7d?.n ?? '—')" tone="#2563eb" tint="#eff6ff"
      />
      <KpiTile
        icon="check-circle" :label="t('Invoices today')" :value="d.invoices_today?.n"
        :sub="money(d.invoices_today?.total)" tone="#059669" tint="#ecfdf5"
      />
      <KpiTile
        icon="alarm" :label="t('Overdue invoices')" :value="d.overdue_invoices?.n"
        :sub="money(d.overdue_invoices?.total)" tone="#e11d48" tint="#fff1f2"
        :pulse="(d.overdue_invoices?.n || 0) > 0"
      />
    </div>

    <!-- risk row -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <RiskTile :label="t('Stuck orders (3d+)')" :value="d.stuck_orders?.n" tone="#d97706" />
      <RiskTile :label="t('Items missing content (30d)')" :value="d.items_missing_content?.n" tone="#7c3aed" />
      <RiskTile :label="t('Hub SLA breached')" :value="d.hub?.breached" tone="#e11d48" />
      <RiskTile :label="t('Open WhatsApp escalations')" :value="d.hub?.joyagent_open" tone="#0d9488" />
    </div>

    <!-- orders trend -->
    <div class="card p-5">
      <h3 class="text-sm font-semibold text-ink-700 mb-4">{{ t("Orders — last 14 days") }}</h3>
      <div class="flex items-end gap-1.5 h-28">
        <div
          v-for="r in d.orders_by_day || []"
          :key="r.d"
          class="flex-1 rounded-t-md bg-brand-200 hover:bg-brand-400 transition relative group"
          :style="{ height: Math.max(4, (r.n / maxDay) * 100) + '%' }"
        >
          <span class="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-bold text-ink-600 opacity-0 group-hover:opacity-100 transition whitespace-nowrap">
            {{ r.n }} · {{ String(r.d).slice(5) }}
          </span>
        </div>
        <p v-if="!(d.orders_by_day || []).length" class="text-sm text-ink-400">{{ t("no data") }}</p>
      </div>
    </div>

    <div class="grid lg:grid-cols-2 gap-4">
      <!-- hub health -->
      <div class="card overflow-hidden">
        <div class="px-5 pt-5 pb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-ink-700">{{ t("Hub health by workspace") }}</h3>
          <span v-if="d.hub?.avg_resolution_7d != null" class="text-[11px] text-ink-400">
            {{ t("Avg resolution") }} (7d): <b class="text-ink-700">{{ d.hub.avg_resolution_7d }}h</b>
          </span>
        </div>
        <div class="divide-y divide-ink-50">
          <button
            v-for="w in d.workspaces || []"
            :key="w.name"
            class="w-full flex items-center gap-3 px-5 py-2.5 hover:bg-ink-50 transition text-left rtl:text-right"
            @click="goWorkspace(w.name)"
          >
            <span>{{ w.icon }}</span>
            <span class="flex-1 text-sm text-ink-800 truncate">{{ w.name }}</span>
            <span v-if="w.breached" class="text-[11px] font-bold text-rose-600">⚠ {{ w.breached }}</span>
            <span class="text-sm font-bold tabular-nums" :style="{ color: w.color }">{{ w.open }}</span>
          </button>
          <p v-if="!(d.workspaces || []).length" class="px-5 py-6 text-sm text-ink-400">
            {{ t("No open tickets — all clear") }}
          </p>
        </div>
      </div>

      <!-- goals -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-ink-700">{{ t("Goals") }}</h3>
          <button class="btn-outline !py-1 text-xs" @click="startNewGoal">+ {{ t("Add goal") }}</button>
        </div>

        <div v-if="goalEdit" class="border border-brand-200 bg-brand-50/40 rounded-xl p-3 mb-3 space-y-2">
          <div class="grid grid-cols-2 gap-2">
            <input v-model="goalEdit.goal_name" class="input !py-1.5 text-sm col-span-2"
                   :placeholder="t('Goal')" :disabled="!!goalEdit.name" />
            <select v-model="goalEdit.workspace" class="input !py-1.5 text-sm">
              <option value="">{{ t("All workspaces") }}</option>
              <option v-for="w in workspaces" :key="w.name" :value="w.name">{{ w.icon }} {{ w.name }}</option>
            </select>
            <select v-model="goalEdit.metric" class="input !py-1.5 text-sm">
              <option value="Tickets resolved">{{ t("Tickets resolved") }}</option>
              <option value="SLA on-time %">{{ t("SLA on-time %") }}</option>
            </select>
            <input v-model.number="goalEdit.target_value" type="number" min="1" class="input !py-1.5 text-sm" :placeholder="t('Target')" />
            <div class="flex gap-2 col-span-2">
              <input v-model="goalEdit.period_start" type="date" class="input !py-1.5 text-sm" />
              <input v-model="goalEdit.period_end" type="date" class="input !py-1.5 text-sm" />
            </div>
          </div>
          <div class="flex justify-end gap-2">
            <button class="btn-outline !py-1 text-xs" @click="goalEdit = null">{{ t("Cancel") }}</button>
            <button class="btn-primary !py-1 text-xs"
                    :disabled="savingGoal || !goalEdit.goal_name.trim() || !goalEdit.target_value || !goalEdit.period_start || !goalEdit.period_end"
                    @click="saveGoalRow">{{ t("Save") }}</button>
          </div>
        </div>

        <div class="space-y-3">
          <div v-for="g in goals" :key="g.name" class="group">
            <div class="flex items-center gap-2 text-sm">
              <span class="font-medium text-ink-800 truncate flex-1">
                {{ g.goal_name }}
                <span class="text-[11px] text-ink-400">· {{ g.workspace || t("All workspaces") }}</span>
              </span>
              <span class="text-[11px] font-bold" :style="{ color: GOAL_META[g.status].color }">
                {{ t(GOAL_META[g.status].label) }}
              </span>
              <span class="text-xs tabular-nums text-ink-600">
                {{ g.current }}/{{ g.target_value }}{{ g.metric === "SLA on-time %" ? "%" : "" }}
              </span>
              <button class="opacity-0 group-hover:opacity-100 btn-ghost !px-1.5 !py-0.5 text-xs" @click="startEditGoal(g)">
                <NavIcon name="pencil" :size="11" />
              </button>
              <button class="opacity-0 group-hover:opacity-100 text-ink-300 hover:text-rose-600 text-xs" @click="removeGoal(g)">✕</button>
            </div>
            <div class="relative h-2 rounded-full bg-ink-100 overflow-hidden mt-1">
              <div class="h-full rounded-full transition-all duration-500"
                   :style="{ width: g.progress_pct + '%', background: GOAL_META[g.status].color }" />
              <!-- where the goal *should* be by today -->
              <div class="absolute top-0 bottom-0 w-0.5 bg-ink-400/60" :style="{ left: g.time_pct + '%' }" />
            </div>
          </div>
          <p v-if="!goals.length && !goalEdit" class="text-sm text-ink-400 py-3">
            {{ t("No goals yet — set a quarterly target per team.") }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// The CEO's one page: today's ERP numbers, operational risk, order momentum,
// hub health, and quarterly goals — the pace marker on each goal bar shows
// where the team *should* be by today.
import { ref, computed, onMounted, onUnmounted, h } from "vue";
import { useRouter } from "vue-router";
import NavIcon from "@/components/NavIcon.vue";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { useWorkspaces } from "@/composables/useWorkspaces";
import { getMethod, callMethod } from "@/composables/useApi";

const { t } = useI18n();
const toast = useToast();
const router = useRouter();
const { workspaces } = useWorkspaces();

const d = ref({});
const goals = ref([]);
const loading = ref(true);
const error = ref("");
const goalEdit = ref(null);
const savingGoal = ref(false);
let timer = null;

const GOAL_META = {
  done: { label: "Done", color: "#059669" },
  on_track: { label: "On track", color: "#2563eb" },
  behind: { label: "Behind", color: "#e11d48" },
};

const maxDay = computed(() =>
  Math.max(1, ...(d.value.orders_by_day || []).map((r) => r.n))
);

function money(v) {
  if (v == null) return "";
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function goWorkspace(name) {
  localStorage.setItem("th_ws", name);
  router.push("/board").then(() => window.location.reload());
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [cc, gl] = await Promise.all([
      getMethod("task_hub.api.command.get_command_center"),
      getMethod("task_hub.api.goals.list_goals"),
    ]);
    d.value = cc;
    goals.value = gl;
  } catch (e) {
    error.value = e.message || "Could not load the command center";
  } finally {
    loading.value = false;
  }
}

function startNewGoal() {
  const now = new Date();
  const q = Math.floor(now.getMonth() / 3);
  const start = new Date(now.getFullYear(), q * 3, 1);
  const end = new Date(now.getFullYear(), q * 3 + 3, 0);
  const iso = (x) => x.toISOString().slice(0, 10);
  goalEdit.value = {
    goal_name: "", workspace: "", metric: "Tickets resolved",
    target_value: 50, period_start: iso(start), period_end: iso(end), active: 1,
  };
}

function startEditGoal(g) {
  goalEdit.value = { ...g };
}

async function saveGoalRow() {
  savingGoal.value = true;
  try {
    await callMethod("task_hub.api.goals.save_goal", { ...goalEdit.value });
    goalEdit.value = null;
    load();
  } catch (e) {
    toast.error(e.message || "Could not save the goal");
  } finally {
    savingGoal.value = false;
  }
}

async function removeGoal(g) {
  try {
    await callMethod("task_hub.api.goals.delete_goal", { name: g.name });
    load();
  } catch (e) {
    toast.error(e.message);
  }
}

// --- tiny presentational tiles ---
const KpiTile = (props) =>
  h("div", { class: "card p-4 relative overflow-hidden" }, [
    h("div", {
      class: "absolute -right-4 -top-4 w-20 h-20 rounded-full opacity-60",
      style: { background: props.tint },
    }),
    h("div", { class: "relative" }, [
      h("span", {
        class: "w-8 h-8 grid place-items-center rounded-xl inline-grid",
        style: { background: props.tint, color: props.tone },
      }, [h(NavIcon, { name: props.icon, size: 16 })]),
      props.pulse
        ? h("span", { class: "absolute top-0 right-0 w-2 h-2 rounded-full animate-pulse", style: { background: props.tone } })
        : null,
      h("div", { class: "text-3xl font-bold mt-2 tabular-nums", style: { color: props.tone } },
        String(props.value ?? "—")),
      h("div", { class: "text-sm font-semibold text-ink-700 mt-0.5" }, props.label),
      h("div", { class: "text-[11px] text-ink-400 tabular-nums" }, props.sub || ""),
    ]),
  ]);
KpiTile.props = ["icon", "label", "value", "sub", "tone", "tint", "pulse"];

const RiskTile = (props) =>
  h("div", { class: "card p-3.5 text-center" }, [
    h("div", { class: "text-2xl font-bold tabular-nums", style: { color: props.value ? props.tone : "#a8a29e" } },
      String(props.value ?? "—")),
    h("div", { class: "text-[11px] text-ink-400 uppercase tracking-wide mt-0.5" }, props.label),
  ]);
RiskTile.props = ["label", "value", "tone"];

onMounted(() => {
  load();
  timer = setInterval(load, 60000);
});
onUnmounted(() => timer && clearInterval(timer));
</script>
