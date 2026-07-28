<template>
  <div class="space-y-4">
    <!-- filter bar -->
    <div class="flex flex-wrap items-center gap-2">
      <select v-model="filters.source_portal" class="input !w-auto" @change="load">
        <option value="">All portals</option>
        <option v-for="p in PORTALS" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.priority" class="input !w-auto" @change="load">
        <option value="">Any priority</option>
        <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
      </select>
      <label class="flex items-center gap-2 text-sm text-ink-600 ml-1">
        <input type="checkbox" v-model="filters.mine" class="rounded" @change="load" />
        My tickets
      </label>
      <label class="flex items-center gap-2 text-sm text-ink-600">
        <input type="checkbox" v-model="filters.breached_only" class="rounded" @change="load" />
        SLA breached
      </label>
      <div class="flex-1" />
      <button class="btn-outline" @click="load">↻ Refresh</button>
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <!-- board -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <div
        v-for="col in BOARD_COLUMNS"
        :key="col"
        class="bg-ink-100/60 rounded-xl p-3 flex flex-col min-h-[200px]"
        @dragover.prevent
        @drop="onDrop(col)"
      >
        <div class="flex items-center justify-between px-1 mb-3">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full" :style="{ background: STATUS_META[col].color }" />
            <span class="text-sm font-semibold text-ink-700">{{ col }}</span>
          </div>
          <span class="text-xs font-bold text-ink-400 bg-white rounded-full px-2 py-0.5">
            {{ grouped[col].length }}
          </span>
        </div>

        <div class="flex-1 space-y-2.5 overflow-y-auto scroll-thin max-h-[calc(100vh-230px)] pr-0.5">
          <div
            v-for="ticket in grouped[col]"
            :key="ticket.name"
            draggable="true"
            @dragstart="dragging = ticket"
            @dragend="dragging = null"
          >
            <TicketCard :ticket="ticket" @open="ui.openTicket" />
          </div>
          <p v-if="!grouped[col].length && !loading" class="text-xs text-ink-400 px-1 py-4 text-center">
            Nothing here
          </p>
        </div>
      </div>
    </div>

    <p v-if="loading" class="text-sm text-ink-400 text-center py-4">Loading tickets…</p>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import TicketCard from "@/components/TicketCard.vue";
import { useUi } from "@/composables/useUi";
import { useToast } from "@/composables/useToast";
import {
  BOARD_COLUMNS, PORTALS, PRIORITIES, STATUS_META, listTickets, updateStatus,
} from "@/composables/useTickets";

const ui = useUi();
const toast = useToast();
const loading = ref(true);
const error = ref("");
const tickets = ref([]);
const dragging = ref(null);

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
      order_by: "priority asc",
    });
    // Only board columns; terminal states (Closed/Cancelled) live in the list view.
    tickets.value = (res.tickets || []).filter((t) => BOARD_COLUMNS.includes(t.status));
  } catch (e) {
    error.value = e.message || "Could not load tickets";
  } finally {
    loading.value = false;
  }
}

async function onDrop(col) {
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

onMounted(load);
watch(() => ui.state.rev, load);
</script>
