<template>
  <div class="space-y-4">
    <!-- filters -->
    <div class="flex flex-wrap items-center gap-2">
      <input
        v-model="filters.search"
        class="input !w-56"
        placeholder="Search title or ID…"
        @keydown.enter="reload"
      />
      <select v-model="filters.status" class="input !w-auto" @change="reload">
        <option value="">Any status</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filters.source_portal" class="input !w-auto" @change="reload">
        <option value="">All portals</option>
        <option v-for="p in PORTALS" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.priority" class="input !w-auto" @change="reload">
        <option value="">Any priority</option>
        <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.ticket_type" class="input !w-auto" @change="reload">
        <option value="">Any type</option>
        <option v-for="tp in TYPES" :key="tp" :value="tp">{{ tp }}</option>
      </select>
      <div class="flex-1" />
      <span class="text-sm text-ink-400">{{ total }} tickets</span>
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <!-- table -->
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-ink-50 text-ink-500 text-left text-xs uppercase tracking-wide">
              <th class="px-4 py-3 font-semibold">Ticket</th>
              <th class="px-3 py-3 font-semibold">Portal</th>
              <th class="px-3 py-3 font-semibold">Priority</th>
              <th class="px-3 py-3 font-semibold">Status</th>
              <th class="px-3 py-3 font-semibold">Assignee</th>
              <th class="px-3 py-3 font-semibold">SLA</th>
              <th class="px-4 py-3 font-semibold">Updated</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="tk in tickets"
              :key="tk.name"
              class="border-t border-ink-100 hover:bg-brand-50/40 cursor-pointer"
              @click="ui.openTicket(tk.name)"
            >
              <td class="px-4 py-3">
                <div class="font-medium text-ink-900 line-clamp-1">{{ tk.title }}</div>
                <div class="text-[11px] font-mono text-ink-400">{{ tk.name }}</div>
              </td>
              <td class="px-3 py-3">
                <span class="text-xs font-medium" :style="{ color: portalColor(tk.source_portal) }">
                  {{ tk.source_portal }}
                </span>
              </td>
              <td class="px-3 py-3">
                <Pill
                  :label="tk.priority"
                  :color="PRIORITY_META[tk.priority].color"
                  :bg="PRIORITY_META[tk.priority].bg"
                  dot
                />
              </td>
              <td class="px-3 py-3">
                <Pill
                  :label="tk.status"
                  :color="STATUS_META[tk.status].color"
                  :bg="STATUS_META[tk.status].bg"
                />
              </td>
              <td class="px-3 py-3 text-ink-600">{{ shortUser(tk.assigned_to) }}</td>
              <td class="px-3 py-3">
                <span v-if="tk.sla_breached" class="text-xs font-bold text-rose-600">Breached</span>
                <span v-else class="text-xs text-ink-500">{{ relTime(tk.sla_deadline) }}</span>
              </td>
              <td class="px-4 py-3 text-ink-400 text-xs whitespace-nowrap">
                {{ relTime(tk.modified) }}
              </td>
            </tr>
            <tr v-if="!tickets.length && !loading">
              <td colspan="7" class="px-4 py-10 text-center text-ink-400">No tickets match.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="flex items-center justify-between">
      <button class="btn-outline" :disabled="start === 0" @click="page(-1)">← Prev</button>
      <span class="text-sm text-ink-400">
        {{ start + 1 }}–{{ Math.min(start + limit, total) }} of {{ total }}
      </span>
      <button class="btn-outline" :disabled="start + limit >= total" @click="page(1)">
        Next →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import Pill from "@/components/Pill.vue";
import { useUi } from "@/composables/useUi";
import {
  STATUSES, PORTALS, PRIORITIES, TYPES, PRIORITY_META, STATUS_META, PORTAL_META,
  listTickets,
} from "@/composables/useTickets";
import { relTime } from "@/composables/useApi";

const ui = useUi();
const loading = ref(true);
const error = ref("");
const tickets = ref([]);
const total = ref(0);
const start = ref(0);
const limit = 25;

const filters = reactive({
  search: "",
  status: "",
  source_portal: "",
  priority: "",
  ticket_type: "",
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await listTickets({
      ...cleaned(),
      limit,
      start: start.value,
      order_by: "modified desc",
    });
    tickets.value = res.tickets || [];
    total.value = res.total || 0;
  } catch (e) {
    error.value = e.message || "Could not load tickets";
  } finally {
    loading.value = false;
  }
}

function cleaned() {
  const o = {};
  for (const [k, v] of Object.entries(filters)) if (v) o[k] = v;
  return o;
}

function reload() {
  start.value = 0;
  load();
}

function page(dir) {
  start.value = Math.max(0, start.value + dir * limit);
  load();
}

function portalColor(p) {
  return (PORTAL_META[p] || PORTAL_META.Other).color;
}
function shortUser(u) {
  return u ? String(u).split("@")[0] : "—";
}

onMounted(load);
watch(() => ui.state.rev, load);
</script>
