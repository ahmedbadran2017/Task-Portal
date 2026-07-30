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
      <button class="btn-outline" @click="load">↻ {{ t("Refresh") }}</button>
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <div v-if="total > tickets.length && !loading"
         class="card p-3 text-xs text-amber-700 bg-amber-50 border-amber-200">
      {{ t("Showing first {0} of {1} tickets — refine the filters.", tickets.length, total) }}
    </div>

    <!-- board: horizontal swipe on mobile, grid on desktop -->
    <div class="board-scroll md:grid md:grid-cols-2 xl:grid-cols-4 md:gap-4">
      <div
        v-for="col in BOARD_COLUMNS"
        :key="col"
        class="rounded-2xl p-3 flex flex-col min-h-[200px] border-t-[3px] transition-colors"
        :style="{ borderTopColor: STATUS_META[col].color }"
        :class="dropTarget === col ? 'bg-brand-50 ring-2 ring-brand-300' : 'bg-ink-100/60'"
        @dragover.prevent="dropTarget = col"
        @dragleave="dropTarget === col && (dropTarget = null)"
        @drop="onDrop(col)"
      >
        <div class="flex items-center justify-between px-1 mb-3">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full" :style="{ background: STATUS_META[col].color }" />
            <span class="text-sm font-semibold text-ink-700">{{ t(col) }}</span>
          </div>
          <span
            class="text-xs font-bold rounded-full px-2 py-0.5"
            :style="{ background: STATUS_META[col].bg, color: STATUS_META[col].color }"
          >
            {{ grouped[col].length }}
          </span>
        </div>

        <div class="flex-1 space-y-2.5 overflow-y-auto scroll-thin max-h-[calc(100vh-230px)] pr-0.5">
          <template v-if="loading && !tickets.length">
            <div class="skeleton h-24" />
            <div class="skeleton h-24 opacity-70" />
          </template>
          <div
            v-for="ticket in grouped[col]"
            :key="ticket.name"
            draggable="true"
            @dragstart="dragging = ticket"
            @dragend="dragging = null"
          >
            <TicketCard
              :ticket="ticket"
              :advance="nextColumn(col)"
              @open="ui.openTicket"
              @advance="advanceTicket"
            />
          </div>
          <p v-if="!grouped[col].length && !loading" class="text-xs text-ink-400 px-1 py-4 text-center">
            {{ t("Nothing here") }}
          </p>
        </div>
      </div>
    </div>

    <p v-if="loading" class="text-sm text-ink-400 text-center py-4">{{ t("Loading tickets…") }}</p>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import TicketCard from "@/components/TicketCard.vue";
import { useUi } from "@/composables/useUi";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";
import {
  BOARD_COLUMNS, PORTALS, PRIORITIES, STATUS_META, listTickets, updateStatus, getSettings,
} from "@/composables/useTickets";

const ui = useUi();
const toast = useToast();
const route = useRoute();
const { t } = useI18n();
const loading = ref(true);
const error = ref("");
const tickets = ref([]);
const total = ref(0);
const dragging = ref(null);
const dropTarget = ref(null);
let refreshTimer = null;

// "priority asc" on the server is alphabetical (High < Low < Medium < Urgent),
// which is meaningless — rank client-side instead.
const PRIORITY_RANK = { Urgent: 0, High: 1, Medium: 2, Low: 3 };

const filters = reactive({
  source_portal: "",
  priority: "",
  mine: false,
  breached_only: false,
});

const grouped = computed(() => {
  const g = Object.fromEntries(BOARD_COLUMNS.map((c) => [c, []]));
  for (const t of tickets.value) {
    if (g[t.status]) g[t.status].push(t);
  }
  for (const c of BOARD_COLUMNS) {
    g[c].sort(
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
      mine: filters.mine ? 1 : 0,
      breached_only: filters.breached_only ? 1 : 0,
      status: undefined,
      limit: 300,
      order_by: "modified desc",
    });
    // Only board columns; terminal states (Closed/Cancelled) live in the list view.
    tickets.value = (res.tickets || []).filter((tk) => BOARD_COLUMNS.includes(tk.status));
    total.value = res.total || 0;
  } catch (e) {
    error.value = e.message || "Could not load tickets";
  } finally {
    loading.value = false;
  }
}

async function onDrop(col) {
  dropTarget.value = null;
  const t = dragging.value;
  dragging.value = null;
  if (!t || t.status === col) return;
  const prev = t.status;
  t.status = col; // optimistic
  try {
    await updateStatus(t.name, col);
    toast.success(`${t.name} → ${col}`);
    ui.bump();
  } catch (e) {
    t.status = prev; // rollback
    toast.error(e.message || "Could not move ticket");
  }
}

function nextColumn(col) {
  const i = BOARD_COLUMNS.indexOf(col);
  return i >= 0 && i < BOARD_COLUMNS.length - 1 ? BOARD_COLUMNS[i + 1] : "";
}

async function advanceTicket(tk) {
  const next = nextColumn(tk.status);
  if (!next) return;
  const prev = tk.status;
  tk.status = next;
  try {
    await updateStatus(tk.name, next);
    toast.success(`${tk.name} → ${next}`);
    ui.bump();
  } catch (e) {
    tk.status = prev;
    toast.error(e.message || "Could not move ticket");
  }
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
</script>
