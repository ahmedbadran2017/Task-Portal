<template>
  <div class="space-y-4">
    <!-- filters -->
    <div class="flex flex-wrap items-center gap-2">
      <input
        v-model="filters.search"
        class="input !w-56"
        :placeholder="t('Search title or ID…')"
        @keydown.enter="reload"
      />
      <select v-model="filters.status" class="input !w-auto" @change="reload">
        <option value="">{{ t("Any status") }}</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ t(s) }}</option>
      </select>
      <select v-model="filters.source_portal" class="input !w-auto" @change="reload">
        <option value="">{{ t("All portals") }}</option>
        <option v-for="p in PORTALS" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.priority" class="input !w-auto" @change="reload">
        <option value="">{{ t("Any priority") }}</option>
        <option v-for="p in PRIORITIES" :key="p" :value="p">{{ t(p) }}</option>
      </select>
      <select v-model="filters.ticket_type" class="input !w-auto" @change="reload">
        <option value="">{{ t("Any type") }}</option>
        <option v-for="tp in TYPES" :key="tp" :value="tp">{{ t(tp) }}</option>
      </select>
      <div class="flex items-center gap-1.5">
        <button
          v-for="c in quickChips"
          :key="c.key"
          class="px-2.5 py-1.5 rounded-full text-xs font-semibold border transition"
          :class="filters[c.key] ? 'bg-brand-50 border-brand-300 text-brand-700' : 'bg-white border-ink-200 text-ink-500 hover:border-ink-300'"
          @click="filters[c.key] = filters[c.key] ? 0 : 1; reload()"
        >
          {{ c.label }}
        </button>
      </div>
      <span
        v-if="filters.department"
        class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-semibold bg-brand-50 border border-brand-300 text-brand-700"
      >
        {{ filters.department }}
        <button class="hover:text-rose-600" @click="filters.department = ''; reload()">✕</button>
      </span>
      <div class="flex-1" />
      <button class="btn-outline !py-1.5 text-xs" @click="exportCsv">⬇ {{ t("Export CSV") }}</button>
      <span class="text-sm text-ink-400">{{ total }} {{ t("tickets") }}</span>
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
              <th class="px-4 py-3 font-semibold">{{ t("Ticket") }}</th>
              <th class="px-3 py-3 font-semibold">{{ t("Portal") }}</th>
              <th class="px-3 py-3 font-semibold">{{ t("Priority") }}</th>
              <th class="px-3 py-3 font-semibold">{{ t("Status") }}</th>
              <th class="px-3 py-3 font-semibold">{{ t("Assignee") }}</th>
              <th class="px-3 py-3 font-semibold">SLA</th>
              <th class="px-4 py-3 font-semibold">{{ t("Updated") }}</th>
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
                  :label="t(tk.priority)"
                  :color="PRIORITY_META[tk.priority].color"
                  :bg="PRIORITY_META[tk.priority].bg"
                  dot
                />
              </td>
              <td class="px-3 py-3">
                <Pill
                  :label="t(tk.status)"
                  :color="STATUS_META[tk.status].color"
                  :bg="STATUS_META[tk.status].bg"
                />
              </td>
              <td class="px-3 py-3">
                <span v-if="tk.assigned_to" class="inline-flex items-center gap-1.5">
                  <span
                    class="w-6 h-6 rounded-full grid place-items-center text-[10px] font-bold text-white"
                    :style="{ background: avatarColor(tk.assigned_to) }"
                  >{{ initials(tk.assigned_to) }}</span>
                  <span class="text-ink-600 text-xs">{{ shortUser(tk.assigned_to) }}</span>
                </span>
                <span v-else class="text-xs text-ink-300">—</span>
              </td>
              <td class="px-3 py-3">
                <span v-if="tk.sla_breached" class="text-xs font-bold text-rose-600">{{ t("Breached") }}</span>
                <span v-else class="text-xs text-ink-500">{{ relTime(tk.sla_deadline) }}</span>
                <span v-if="tk.due_date" class="block text-[10px] text-ink-400 mt-0.5">📅 {{ tk.due_date }}</span>
              </td>
              <td class="px-4 py-3 text-ink-400 text-xs whitespace-nowrap">
                {{ relTime(tk.modified) }}
              </td>
            </tr>
            <tr v-for="i in (loading && !tickets.length ? 5 : 0)" :key="'sk' + i">
              <td colspan="7" class="px-4 py-2"><div class="skeleton h-9" /></td>
            </tr>
            <tr v-if="!tickets.length && !loading">
              <td colspan="7" class="px-4 py-10 text-center text-ink-400">{{ t("No tickets match.") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="flex items-center justify-between">
      <button class="btn-outline" :disabled="start === 0" @click="page(-1)">← {{ t("Prev") }}</button>
      <span class="text-sm text-ink-400">
        {{ start + 1 }}–{{ Math.min(start + limit, total) }} {{ t("of") }} {{ total }}
      </span>
      <button class="btn-outline" :disabled="start + limit >= total" @click="page(1)">
        {{ t("Next") }} →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import Pill from "@/components/Pill.vue";
import { useUi } from "@/composables/useUi";
import { useI18n } from "@/composables/useI18n";
import { useWorkspaces } from "@/composables/useWorkspaces";
import {
  STATUSES, PORTALS, PRIORITIES, TYPES, PRIORITY_META, STATUS_META, PORTAL_META,
  listTickets,
} from "@/composables/useTickets";
import { relTime } from "@/composables/useApi";

const ui = useUi();
const { t } = useI18n();
const { current: currentWsName } = useWorkspaces();
const loading = ref(true);
const error = ref("");
const tickets = ref([]);
const total = ref(0);
const start = ref(0);
const limit = 25;

const route = useRoute();

const filters = reactive({
  search: "",
  status: "",
  source_portal: "",
  priority: "",
  ticket_type: "",
  breached_only: 0,
  mine: 0,
  unassigned: 0,
  department: "",
});

const quickChips = [
  { key: "mine", label: t("Mine") },
  { key: "unassigned", label: t("Unassigned") },
  { key: "breached_only", label: t("SLA breached") },
];

// Dashboard tiles deep-link here (?breached=1, ?mine=1, ?unassigned=1, ?status=…)
function applyRouteQuery() {
  const q = route.query || {};
  filters.breached_only = q.breached ? 1 : 0;
  filters.mine = q.mine ? 1 : 0;
  filters.unassigned = q.unassigned ? 1 : 0;
  if (typeof q.status === "string" && STATUSES.includes(q.status)) filters.status = q.status;
  filters.department = typeof q.department === "string" ? q.department : "";
  if (typeof q.portal === "string" && PORTALS.includes(q.portal)) filters.source_portal = q.portal;
  // Email deep links: /taskhub/tickets?open=TKT-… pops the ticket card open.
  if (typeof q.open === "string" && q.open) ui.openTicket(q.open);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await listTickets({
      ...cleaned(),
      workspace: currentWsName.value || undefined,
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

async function exportCsv() {
  try {
    const res = await listTickets({ ...cleaned(), limit: 1000, start: 0, order_by: "modified desc" });
    const rows = res.tickets || [];
    const cols = ["name", "title", "ticket_type", "priority", "status", "source_portal",
                  "department", "reported_by", "assigned_to", "due_date", "sla_deadline",
                  "sla_breached", "resolved_on", "creation"];
    const esc = (v) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
    const csv = [cols.join(",")]
      .concat(rows.map((r) => cols.map((c) => esc(r[c])).join(",")))
      .join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "task-hub-tickets.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    error.value = e.message || "Export failed";
  }
}

function portalColor(p) {
  return (PORTAL_META[p] || PORTAL_META.Other).color;
}
function shortUser(u) {
  return u ? String(u).split("@")[0] : "—";
}
const AVATAR_COLORS = ["#d45d3e", "#7c3aed", "#059669", "#2563eb", "#d97706", "#0891b2", "#9f1239"];
function avatarColor(u) {
  let hash = 0;
  for (const ch of String(u)) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}
function initials(u) {
  return String(u).split("@")[0].slice(0, 2).toUpperCase();
}

onMounted(() => {
  applyRouteQuery();
  load();
});
watch(() => ui.state.rev, load);
watch(() => route.query, () => {
  applyRouteQuery();
  reload();
});
</script>
