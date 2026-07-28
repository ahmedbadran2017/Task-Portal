<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <!-- KPI row — each tile jumps to the matching filtered view -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <StatTile
        icon="◎" label="Open" :value="t.open" tone="#3b82f6" tint="#eff6ff"
        hint="tickets in progress" @click="go('/board')"
      />
      <StatTile
        icon="⏰" label="SLA Breached" :value="t.breached" tone="#e11d48" tint="#fff1f2"
        hint="past deadline" :pulse="t.breached > 0" @click="go('/tickets', { breached: 1 })"
      />
      <StatTile
        icon="◑" label="My Queue" :value="t.mine_open" tone="#7c3aed" tint="#f5f3ff"
        hint="assigned to me" @click="go('/tickets', { mine: 1 })"
      />
      <StatTile
        icon="○" label="Unassigned" :value="t.unassigned" tone="#d97706" tint="#fffbeb"
        hint="need an owner" @click="go('/tickets', { unassigned: 1 })"
      />
    </div>

    <div class="grid lg:grid-cols-2 gap-4">
      <!-- by portal -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-ink-700 mb-4">Open work by portal</h3>
        <div v-if="loading" class="text-sm text-ink-400">Loading…</div>
        <div v-else class="space-y-3">
          <BarRow
            v-for="row in byPortal"
            :key="row.portal"
            :label="row.portal"
            :value="row.count"
            :max="maxPortal"
            :color="portalColor(row.portal)"
          />
          <div v-if="!byPortal.length" class="text-center py-6">
            <div class="text-3xl mb-2">🎉</div>
            <p class="text-sm text-ink-400">No open tickets — all clear</p>
          </div>
        </div>
      </div>

      <!-- by priority -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-ink-700 mb-4">Open by priority</h3>
        <div v-if="loading" class="text-sm text-ink-400">Loading…</div>
        <div v-else class="space-y-3">
          <BarRow
            v-for="p in PRIORITIES"
            :key="p"
            :label="p"
            :value="priorityCount(p)"
            :max="maxPriority"
            :color="PRIORITY_META[p].color"
          />
        </div>
      </div>
    </div>

    <!-- status breakdown chips -->
    <div class="card p-5">
      <h3 class="text-sm font-semibold text-ink-700 mb-4">Everything, by status</h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="s in STATUSES"
          :key="s"
          class="px-3 py-2 rounded-xl border border-ink-200 flex items-center gap-2 hover:border-ink-300 hover:bg-ink-50 transition"
          @click="go('/tickets', { status: s })"
        >
          <span class="w-2 h-2 rounded-full" :style="{ background: STATUS_META[s].color }" />
          <span class="text-sm text-ink-700">{{ s }}</span>
          <span class="text-sm font-bold text-ink-900">{{ statusCount(s) }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, h } from "vue";
import { useRouter } from "vue-router";
import { useUi } from "@/composables/useUi";
import {
  getSummary, getSettings, PRIORITIES, STATUSES, PRIORITY_META, STATUS_META, PORTAL_META,
} from "@/composables/useTickets";

const ui = useUi();
const router = useRouter();
const loading = ref(true);
const error = ref("");
const summary = ref({ totals: {}, by_portal: [], by_status: [], by_priority: [] });
let refreshTimer = null;

const t = computed(() => ({
  open: summary.value.totals.open || 0,
  breached: summary.value.totals.breached || 0,
  mine_open: summary.value.totals.mine_open || 0,
  unassigned: summary.value.totals.unassigned || 0,
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
    if (secs > 0) refreshTimer = setInterval(() => getSummary().then((d) => (summary.value = d)).catch(() => {}), secs * 1000);
  } catch {}
}

onMounted(() => {
  load();
  armAutoRefresh();
});
onUnmounted(() => refreshTimer && clearInterval(refreshTimer));
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
        class: "absolute -right-4 -top-4 w-20 h-20 rounded-full opacity-60",
        style: { background: props.tint },
      }),
      h("div", { class: "relative" }, [
        h("div", { class: "flex items-center justify-between" }, [
          h(
            "span",
            {
              class: "w-8 h-8 grid place-items-center rounded-xl text-base",
              style: { background: props.tint, color: props.tone },
            },
            props.icon
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

const BarRow = (props) =>
  h("div", { class: "flex items-center gap-3" }, [
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
</script>
