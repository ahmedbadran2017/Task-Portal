<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <!-- Ask the Hub — natural-language questions over your visible tickets -->
    <div v-if="aiOn" class="card p-4">
      <form class="flex items-center gap-2" @submit.prevent="doAsk">
        <span class="w-8 h-8 grid place-items-center rounded-xl bg-brand-50 text-brand-600 shrink-0">
          <NavIcon name="sparkles" :size="15" />
        </span>
        <input
          v-model="askQ"
          class="input !py-2"
          :placeholder="t('Ask about your work… e.g. what is late? who is overloaded?')"
          maxlength="500"
        />
        <button class="btn-primary !py-2" type="submit" :disabled="asking || !askQ.trim()">
          {{ asking ? "…" : t("Ask") }}
        </button>
      </form>
      <div v-if="askA" class="mt-3 text-sm text-ink-800 leading-relaxed bg-brand-50/50 border border-brand-100 rounded-xl px-3.5 py-3 whitespace-pre-wrap fade-up" v-html="askA" />
    </div>

    <!-- KPI row — each tile jumps to the matching filtered view -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <StatTile
        icon="circle-dot" :label="t('Open')" :value="kpi.open" tone="#3b82f6" tint="#eff6ff"
        :hint="t('tickets in progress')" @click="go('/board')"
      />
      <StatTile
        icon="alarm" :label="t('SLA Breached')" :value="kpi.breached" tone="#e11d48" tint="#fff1f2"
        :hint="t('past deadline')" :pulse="kpi.breached > 0" @click="go('/tickets', { breached: 1 })"
      />
      <StatTile
        icon="inbox" :label="t('My Queue')" :value="kpi.mine_open" tone="#7c3aed" tint="#f5f3ff"
        :hint="t('assigned to me')" @click="go('/tickets', { mine: 1 })"
      />
      <!-- managers triage the unassigned pool; everyone else tracks what they reported -->
      <StatTile
        v-if="manager"
        icon="circle-dashed" :label="t('Unassigned')" :value="kpi.unassigned" tone="#d97706" tint="#fffbeb"
        :hint="t('need an owner')" @click="go('/tickets', { unassigned: 1 })"
      />
      <StatTile
        v-else
        icon="flag" :label="t('Reported by me')" :value="kpi.reported_open" tone="#d97706" tint="#fffbeb"
        :hint="t('opened by me')" @click="go('/tickets', { reported: 1 })"
      />
    </div>

    <div class="grid lg:grid-cols-2 gap-4">
      <!-- by portal -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-ink-700 mb-4">{{ t("Open work by portal") }}</h3>
        <div v-if="loading" class="text-sm text-ink-400">{{ t("Loading…") }}</div>
        <div v-else class="space-y-3">
          <BarRow
            v-for="row in byPortal"
            :key="row.portal"
            :label="row.portal"
            :value="row.count"
            :max="maxPortal"
            :color="portalColor(row.portal)"
            @click="go('/tickets', { portal: row.portal })"
          />
          <div v-if="!byPortal.length" class="text-center py-6">
            <NavIcon name="check-circle" :size="28" class="inline-block mb-2 text-emerald-500" />
            <p class="text-sm text-ink-400">{{ t("No open tickets — all clear") }}</p>
          </div>
        </div>
      </div>

      <!-- by priority -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-ink-700 mb-4">{{ t("Open by priority") }}</h3>
        <div v-if="loading" class="text-sm text-ink-400">{{ t("Loading…") }}</div>
        <div v-else class="space-y-3">
          <BarRow
            v-for="p in PRIORITIES"
            :key="p"
            :label="t(p)"
            :value="priorityCount(p)"
            :max="maxPriority"
            :color="PRIORITY_META[p].color"
          />
        </div>
      </div>
    </div>

    <!-- trends + roll-up -->
    <div class="card p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-ink-700">{{ t("Created vs resolved — last 8 weeks") }}</h3>
      </div>
      <TrendChart :series="trends.series" />
    </div>

    <div v-if="trends.health.length" class="card overflow-hidden">
      <h3 class="text-sm font-semibold text-ink-700 px-5 pt-5 pb-3">{{ t("Portal health (30 days)") }}</h3>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-ink-50 text-ink-500 text-left rtl:text-right text-xs uppercase tracking-wide">
              <th class="px-5 py-2.5 font-semibold">{{ t("Portal") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Open") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Breached") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Resolved (30d)") }}</th>
              <th class="px-5 py-2.5 font-semibold">{{ t("Avg resolution") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in trends.health" :key="row.portal" class="border-t border-ink-100">
              <td class="px-5 py-3">
                <span class="inline-flex items-center gap-2 font-medium text-ink-800">
                  <span class="w-2 h-2 rounded-full" :style="{ background: portalColor(row.portal) }" />
                  {{ row.portal }}
                </span>
              </td>
              <td class="px-3 py-3 tabular-nums">{{ row.open }}</td>
              <td class="px-3 py-3 tabular-nums">
                <span :class="row.breached ? 'text-rose-600 font-bold' : 'text-ink-400'">{{ row.breached }}</span>
              </td>
              <td class="px-3 py-3 tabular-nums">{{ row.resolved_30d }}</td>
              <td class="px-5 py-3 text-ink-600">
                {{ row.avg_resolution_hours != null ? row.avg_resolution_hours + "h" : "—" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- status breakdown chips -->
    <div class="card p-5">
      <h3 class="text-sm font-semibold text-ink-700 mb-4">{{ t("Everything, by status") }}</h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="s in STATUSES"
          :key="s"
          class="px-3 py-2 rounded-xl border border-ink-200 flex items-center gap-2 hover:border-ink-300 hover:bg-ink-50 transition"
          @click="go('/tickets', { status: s })"
        >
          <span class="w-2 h-2 rounded-full" :style="{ background: STATUS_META[s].color }" />
          <span class="text-sm text-ink-700">{{ t(s) }}</span>
          <span class="text-sm font-bold text-ink-900">{{ statusCount(s) }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, h } from "vue";
import { useRouter } from "vue-router";
import TrendChart from "@/components/TrendChart.vue";
import NavIcon from "@/components/NavIcon.vue";
import { useUi } from "@/composables/useUi";
import { useI18n } from "@/composables/useI18n";
import { useAi } from "@/composables/useAi";
import { useToast } from "@/composables/useToast";
import { isManager } from "@/composables/useApi";
import {
  getSummary, getSettings, getTrends, PRIORITIES, STATUSES, PRIORITY_META, STATUS_META, PORTAL_META,
  askHub,
} from "@/composables/useTickets";

const ui = useUi();
const { t } = useI18n();
const toast = useToast();
const manager = isManager();
const router = useRouter();

// --- Ask the Hub ---
const { enabled: aiOn, ensure: ensureAi } = useAi();
const askQ = ref("");
const askA = ref("");
const asking = ref(false);

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function doAsk() {
  if (asking.value || !askQ.value.trim()) return;
  asking.value = true;
  askA.value = "";
  try {
    const res = await askHub(askQ.value.trim());
    // Linkify ticket IDs so the answer opens the drawer directly.
    askA.value = escapeHtml(res.answer || "").replace(
      /TKT-\d{4}-\d{5}/g,
      (m) => `<a href="/taskhub/tickets?open=${m}" class="text-brand-600 font-semibold hover:underline">${m}</a>`
    );
  } catch (e) {
    toast.error(e.message || "Ask failed");
  } finally {
    asking.value = false;
  }
}
const loading = ref(true);
const error = ref("");
const summary = ref({ totals: {}, by_portal: [], by_status: [], by_priority: [] });
const trends = ref({ series: [], health: [] });
let refreshTimer = null;
// The interval is armed after an await, so a fast unmount would otherwise
// create it on a dead component and leak a forever-polling timer.
let alive = true;

const kpi = computed(() => ({
  open: summary.value.totals.open || 0,
  breached: summary.value.totals.breached || 0,
  mine_open: summary.value.totals.mine_open || 0,
  unassigned: summary.value.totals.unassigned || 0,
  reported_open: summary.value.totals.reported_open || 0,
}));

const byPortal = computed(() => summary.value.by_portal || []);
const maxPortal = computed(() => Math.max(1, ...byPortal.value.map((r) => r.count)));
const maxPriority = computed(() =>
  Math.max(1, ...PRIORITIES.map((p) => priorityCount(p)))
);

function priorityCount(p) {
  return (summary.value.by_priority.find((r) => r.priority === p) || {}).count || 0;
}
function statusCount(s) {
  return (summary.value.by_status.find((r) => r.status === s) || {}).count || 0;
}
function portalColor(p) {
  return (PORTAL_META[p] || PORTAL_META.Other).color;
}

function go(path, query = {}) {
  router.push({ path, query });
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    summary.value = await getSummary();
    trends.value = await getTrends();
  } catch (e) {
    error.value = e.message || "Could not load dashboard";
  } finally {
    loading.value = false;
  }
}

async function armAutoRefresh() {
  try {
    const s = await getSettings();
    const secs = Number(s.auto_refresh_seconds) || 0;
    if (secs > 0 && alive) {
      refreshTimer = setInterval(
        () => getSummary().then((d) => (summary.value = d)).catch(() => {}),
        secs * 1000);
    }
  } catch {}
}

onMounted(() => {
  load();
  armAutoRefresh();
  ensureAi();
});
onUnmounted(() => {
  alive = false;
  if (refreshTimer) clearInterval(refreshTimer);
});
watch(() => ui.state.rev, load);

// --- tiny inline presentational components ---
const StatTile = (props, { emit }) =>
  h(
    "button",
    {
      class: "card card-hover p-4 text-left w-full relative overflow-hidden",
      onClick: () => emit("click"),
    },
    [
      h("div", {
        class: "absolute -right-4 rtl:-right-auto rtl:-left-4 -top-4 w-20 h-20 rounded-full opacity-60",
        style: { background: props.tint },
      }),
      h("div", { class: "relative" }, [
        h("div", { class: "flex items-center justify-between" }, [
          h(
            "span",
            {
              class: "w-8 h-8 grid place-items-center rounded-xl",
              style: { background: props.tint, color: props.tone },
            },
            [h(NavIcon, { name: props.icon, size: 16 })]
          ),
          props.pulse
            ? h("span", { class: "w-2 h-2 rounded-full animate-pulse", style: { background: props.tone } })
            : null,
        ]),
        h(
          "div",
          { class: "text-3xl font-bold mt-2 tabular-nums", style: { color: props.tone } },
          String(props.value)
        ),
        h("div", { class: "text-sm font-semibold text-ink-700 mt-0.5" }, props.label),
        h("div", { class: "text-[11px] text-ink-400" }, props.hint),
      ]),
    ]
  );
StatTile.props = ["icon", "label", "value", "tone", "tint", "hint", "pulse"];
StatTile.emits = ["click"];

const BarRow = (props, { emit }) =>
  h("div", {
    class: "flex items-center gap-3 cursor-pointer rounded-lg px-1 -mx-1 hover:bg-ink-50 transition",
    onClick: () => emit("click"),
  }, [
    h("div", { class: "w-24 text-sm text-ink-600 shrink-0" }, props.label),
    h("div", { class: "flex-1 h-2.5 rounded-full bg-ink-100 overflow-hidden" }, [
      h("div", {
        class: "h-full rounded-full transition-all duration-500",
        style: {
          width: `${Math.round((props.value / props.max) * 100)}%`,
          background: props.color,
          minWidth: props.value ? "6px" : "0",
        },
      }),
    ]),
    h("div", { class: "w-8 text-right text-sm font-semibold text-ink-800" }, String(props.value)),
  ]);
BarRow.props = ["label", "value", "max", "color"];
BarRow.emits = ["click"];
</script>
