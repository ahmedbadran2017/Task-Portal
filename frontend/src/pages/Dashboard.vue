<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <!-- KPI row -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      <StatTile label="Open" :value="t.open" tone="#3b82f6" hint="tickets in progress" />
      <StatTile label="SLA Breached" :value="t.breached" tone="#e11d48" hint="past deadline" />
      <StatTile label="My Queue" :value="t.mine_open" tone="#7c3aed" hint="assigned to me" />
      <StatTile label="Unassigned" :value="t.unassigned" tone="#d97706" hint="need an owner" />
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
          <p v-if="!byPortal.length" class="text-sm text-ink-400">No open tickets 🎉</p>
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
        <div
          v-for="s in STATUSES"
          :key="s"
          class="px-3 py-2 rounded-lg border border-ink-200 flex items-center gap-2"
        >
          <span class="w-2 h-2 rounded-full" :style="{ background: STATUS_META[s].color }" />
          <span class="text-sm text-ink-700">{{ s }}</span>
          <span class="text-sm font-bold text-ink-900">{{ statusCount(s) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, h } from "vue";
import { useUi } from "@/composables/useUi";
import {
  getSummary, PRIORITIES, STATUSES, PRIORITY_META, STATUS_META, PORTAL_META,
} from "@/composables/useTickets";

const ui = useUi();
const loading = ref(true);
const error = ref("");
const summary = ref({ totals: {}, by_portal: [], by_status: [], by_priority: [] });

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

onMounted(load);
watch(() => ui.state.rev, load);

// --- tiny inline presentational components ---
const StatTile = (props) =>
  h("div", { class: "card p-4" }, [
    h("div", { class: "text-3xl font-bold", style: { color: props.tone } }, String(props.value)),
    h("div", { class: "text-sm font-semibold text-ink-700 mt-1" }, props.label),
    h("div", { class: "text-[11px] text-ink-400" }, props.hint),
  ]);
StatTile.props = ["label", "value", "tone", "hint"];

const BarRow = (props) =>
  h("div", { class: "flex items-center gap-3" }, [
    h("div", { class: "w-24 text-sm text-ink-600 shrink-0" }, props.label),
    h("div", { class: "flex-1 h-2.5 rounded-full bg-ink-100 overflow-hidden" }, [
      h("div", {
        class: "h-full rounded-full",
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
