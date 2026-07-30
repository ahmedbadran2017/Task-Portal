<template>
  <div class="space-y-4">
    <!-- filter bar -->
    <div class="flex flex-wrap items-center gap-2">
      <select v-model="filters.source_portal" class="input !w-auto" @change="load">
        <option value="">{{ t("All portals") }}</option>
        <option v-for="p in PORTALS" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.priority" class="input !w-auto" @change="load">
        <option value="">{{ t("Any priority") }}</option>
        <option v-for="p in PRIORITIES" :key="p" :value="p">{{ t(p) }}</option>
      </select>
      <label class="flex items-center gap-2 text-sm text-ink-600 ml-1">
        <input type="checkbox" v-model="filters.mine" class="rounded" @change="load" />
        {{ t("My tickets") }}
      </label>
      <label class="flex items-center gap-2 text-sm text-ink-600">
        <input type="checkbox" v-model="filters.breached_only" class="rounded" @change="load" />
        {{ t("SLA breached") }}
      </label>
      <div class="flex-1" />
      <div class="inline-flex rounded-xl border border-ink-200 overflow-hidden">
        <button
          class="px-3 py-2 text-xs font-semibold transition"
          :class="view === 'board' ? 'bg-brand-500 text-white' : 'bg-white text-ink-600 hover:bg-ink-50'"
          @click="setView('board')"
        >▦ {{ t("Board") }}</button>
        <button
          class="px-3 py-2 text-xs font-semibold transition"
          :class="view === 'calendar' ? 'bg-brand-500 text-white' : 'bg-white text-ink-600 hover:bg-ink-50'"
          @click="setView('calendar')"
        >📅 {{ t("Calendar") }}</button>
      </div>
      <button v-if="view === 'board'" class="btn-outline" @click="load">↻ {{ t("Refresh") }}</button>
    </div>

    <CalendarView v-if="view === 'calendar'" />

    <template v-if="view === 'board'">

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <div v-if="total > tickets.length && !loading"
         class="card p-3 text-xs text-amber-700 bg-amber-50 border-amber-200">
      {{ t("Showing first {0} of {1} tickets — refine the filters.", tickets.length, total) }}
    </div>

    <!-- board: horizontal swipe on mobile, grid on desktop -->
    <div
      class="board-scroll md:grid md:gap-4"
      :style="{ '--cols': columns.length }"
      :class="columns.length > 4 ? 'md:grid-cols-3 xl:grid-cols-6' : 'md:grid-cols-2 xl:grid-cols-4'"
    >
      <div
        v-for="col in columns"
        :key="col.key"
        class="rounded-2xl p-3 flex flex-col min-h-[200px] border-t-[3px] transition-colors"
        :style="{ borderTopColor: col.color }"
        :class="dropTarget === col.key ? 'bg-brand-50 ring-2 ring-brand-300' : 'bg-ink-100/60'"
        @dragover.prevent="dropTarget = col.key"
        @dragleave="dropTarget === col.key && (dropTarget = null)"
        @drop="onDrop(col)"
      >
        <div class="flex items-center justify-between px-1 mb-3">
          <div class="flex items-center gap-2 min-w-0">
            <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: col.color }" />
            <span class="text-sm font-semibold text-ink-700 truncate">{{ col.label }}</span>
          </div>
          <span
            class="text-xs font-bold rounded-full px-2 py-0.5 shrink-0"
            :style="{ background: col.color + '22', color: col.color }"
          >
            {{ grouped[col.key]?.length || 0 }}
          </span>
        </div>

        <div class="flex-1 space-y-2.5 overflow-y-auto scroll-thin max-h-[calc(100vh-230px)] pr-0.5">
          <template v-if="loading && !tickets.length">
            <div class="skeleton h-24" />
            <div class="skeleton h-24 opacity-70" />
          </template>
          <div
            v-for="ticket in grouped[col.key] || []"
            :key="ticket.name"
            draggable="true"
            @dragstart="dragging = ticket"
            @dragend="dragging = null"
          >
            <TicketCard
              :ticket="ticket"
              :advance="nextColumnLabel(col)"
              @open="ui.openTicket"
              @advance="advanceTicket(ticket, col)"
            />
          </div>
          <p v-if="!(grouped[col.key] || []).length && !loading" class="text-xs text-ink-400 px-1 py-4 text-center">
            {{ t("Nothing here") }}
          </p>
        </div>
      </div>
    </div>

    <p v-if="loading" class="text-sm text-ink-400 text-center py-4">{{ t("Loading tickets…") }}</p>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import TicketCard from "@/components/TicketCard.vue";
import CalendarView from "@/components/CalendarView.vue";
import { useUi } from "@/composables/useUi";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";
import { useWorkspaces } from "@/composables/useWorkspaces";
import {
  BOARD_COLUMNS, PORTALS, PRIORITIES, STATUS_META, listTickets, updateStatus, getSettings,
} from "@/composables/useTickets";

const ui = useUi();
const toast = useToast();
const route = useRoute();
const { t } = useI18n();
const { current: currentWsName, currentWs, moveStage } = useWorkspaces();

const view = ref(localStorage.getItem("th_view") || "board");
function setView(v) {
  view.value = v;
  localStorage.setItem("th_view", v);
}

const loading = ref(true);
const error = ref("");
const tickets = ref([]);
const total = ref(0);
const dragging = ref(null);
const dropTarget = ref(null);
let refreshTimer = null;

const PRIORITY_RANK = { Urgent: 0, High: 1, Medium: 2, Low: 3 };

const filters = reactive({
  source_portal: "",
  priority: "",
  mine: false,
  breached_only: false,
});

// Columns: the workspace's own stages, or the canonical statuses in All mode.
const columns = computed(() => {
  if (currentWs.value?.stages?.length) {
    return currentWs.value.stages.map((s) => ({
      key: s.stage_name,
      label: t(s.stage_name),
      color: s.color || "#78716c",
      maps_to: s.maps_to,
      mode: "stage",
    }));
  }
  return BOARD_COLUMNS.map((s) => ({
    key: s,
    label: t(s),
    color: STATUS_META[s].color,
    maps_to: s,
    mode: "status",
  }));
});

const grouped = computed(() => {
  const g = Object.fromEntries(columns.value.map((c) => [c.key, []]));
  const stageMode = !!currentWs.value?.stages?.length;
  for (const tk of tickets.value) {
    let key;
    if (stageMode) {
      key = g[tk.stage] !== undefined ? tk.stage
        // Unknown stage (renamed?) — fall back to the column matching status.
        : columns.value.find((c) => c.maps_to === tk.status)?.key;
    } else {
      key = tk.status;
    }
    if (key && g[key]) g[key].push(tk);
  }
  for (const c of columns.value) {
    g[c.key].sort(
      (a, b) =>
        (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9) ||
        (a.sla_deadline || "z").localeCompare(b.sla_deadline || "z")
    );
  }
  return g;
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await listTickets({
      source_portal: filters.source_portal || undefined,
      priority: filters.priority || undefined,
      workspace: currentWsName.value || undefined,
      mine: filters.mine ? 1 : 0,
      breached_only: filters.breached_only ? 1 : 0,
      limit: 300,
      order_by: "modified desc",
    });
    const all = res.tickets || [];
    // All-mode keeps the classic four columns; a workspace shows every stage,
    // including its done/cancelled ones.
    tickets.value = currentWs.value
      ? all
      : all.filter((tk) => BOARD_COLUMNS.includes(tk.status));
    total.value = res.total || 0;
  } catch (e) {
    error.value = e.message || "Could not load tickets";
  } finally {
    loading.value = false;
  }
}

async function moveTo(tk, col) {
  const prevStage = tk.stage, prevStatus = tk.status;
  tk.stage = col.mode === "stage" ? col.key : tk.stage;
  tk.status = col.maps_to;
  try {
    if (col.mode === "stage") await moveStage(tk.name, col.key);
    else await updateStatus(tk.name, col.key);
    toast.success(`${tk.name} → ${col.label}`);
    ui.bump();
  } catch (e) {
    tk.stage = prevStage;
    tk.status = prevStatus;
    toast.error(e.message || "Could not move ticket");
  }
}

async function onDrop(col) {
  dropTarget.value = null;
  const tk = dragging.value;
  dragging.value = null;
  if (!tk) return;
  const already = col.mode === "stage" ? tk.stage === col.key : tk.status === col.key;
  if (!already) await moveTo(tk, col);
}

function nextColumnLabel(col) {
  const i = columns.value.findIndex((c) => c.key === col.key);
  return i >= 0 && i < columns.value.length - 1 ? columns.value[i + 1].label : "";
}

async function advanceTicket(tk, col) {
  const i = columns.value.findIndex((c) => c.key === col.key);
  if (i < 0 || i >= columns.value.length - 1) return;
  await moveTo(tk, columns.value[i + 1]);
}

onMounted(async () => {
  load();
  if (route.query.new) ui.openCreate();
  try {
    const s = await getSettings();
    const secs = Number(s.auto_refresh_seconds) || 0;
    if (secs > 0) refreshTimer = setInterval(load, secs * 1000);
  } catch {}
});
onUnmounted(() => refreshTimer && clearInterval(refreshTimer));
watch(() => ui.state.rev, load);
watch(currentWsName, load);
</script>
