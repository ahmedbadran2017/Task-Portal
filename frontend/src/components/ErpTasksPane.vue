<template>
  <div class="card overflow-hidden">
    <div class="px-4 py-3 border-b border-ink-100 flex items-center gap-3">
      <span class="text-sm font-bold text-ink-900">{{ t("ERP Tasks") }}</span>
      <span class="text-[11px] text-ink-400">{{ t("Read-only — managed in the Purchasing portal") }}</span>
      <div class="flex-1" />
      <select v-model="statusFilter" class="input !w-auto !py-1.5 text-xs" @change="reload">
        <option value="open">{{ t("Open") }}</option>
        <option value="">{{ t("Any status") }}</option>
        <option value="Completed">{{ t("Resolved") }}</option>
      </select>
      <span class="text-xs text-ink-400">{{ total }}</span>
    </div>

    <div v-if="error" class="p-4 text-sm text-rose-600 bg-rose-50">{{ error }}</div>

    <div class="divide-y divide-ink-50">
      <a
        v-for="tk in tasks"
        :key="tk.name"
        :href="'/app/task/' + tk.name"
        target="_blank"
        rel="noopener"
        class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50 transition"
      >
        <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: statusColor(tk.status) }" />
        <span class="min-w-0 flex-1">
          <span class="block text-sm text-ink-800 truncate">{{ tk.subject }}</span>
          <span class="block text-[11px] text-ink-400">
            {{ tk.name }}<template v-if="tk.assignees.length"> · {{ tk.assignees.map(shortUser).join(", ") }}</template>
          </span>
        </span>
        <span v-if="tk.exp_end_date" class="text-[11px] text-ink-400 inline-flex items-center gap-1 shrink-0">
          <NavIcon name="calendar" :size="10" /> {{ tk.exp_end_date }}
        </span>
        <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0"
              :style="{ color: statusColor(tk.status), background: statusColor(tk.status) + '18' }">
          {{ tk.status }}
        </span>
      </a>
      <div v-for="i in (loading && !tasks.length ? 4 : 0)" :key="'sk' + i" class="px-4 py-2">
        <div class="skeleton h-9" />
      </div>
      <p v-if="!tasks.length && !loading" class="px-4 py-10 text-center text-sm text-ink-400">
        {{ t("Nothing here") }}
      </p>
    </div>

    <div v-if="total > limit" class="flex items-center justify-between px-4 py-3 border-t border-ink-100">
      <button class="btn-outline !py-1.5 text-xs" :disabled="start === 0" @click="page(-1)">← {{ t("Prev") }}</button>
      <span class="text-xs text-ink-400">{{ start + 1 }}–{{ Math.min(start + limit, total) }} {{ t("of") }} {{ total }}</span>
      <button class="btn-outline !py-1.5 text-xs" :disabled="start + limit >= total" @click="page(1)">{{ t("Next") }} →</button>
    </div>
  </div>
</template>

<script setup>
// Read-only window onto core ERPNext Tasks (Purchasing's Selections
// workflow) — shown inside the Purchasing workspace so their work is
// visible from the Hub without duplicating it.
import { ref, onMounted } from "vue";
import NavIcon from "./NavIcon.vue";
import { useI18n } from "@/composables/useI18n";
import { getMethod } from "@/composables/useApi";

const { t } = useI18n();
const tasks = ref([]);
const total = ref(0);
const start = ref(0);
const limit = 50;
const loading = ref(true);
const error = ref("");
const statusFilter = ref("open");

const STATUS_COLORS = {
  Open: "#3b82f6", Working: "#a16207", "Pending Review": "#7c3aed",
  Overdue: "#e11d48", Template: "#64748b", Completed: "#059669", Cancelled: "#9f1239",
};
function statusColor(s) {
  return STATUS_COLORS[s] || "#64748b";
}
function shortUser(u) {
  return String(u || "").split("@")[0];
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await getMethod("task_hub.api.erp_tasks.list_selection_tasks", {
      status: statusFilter.value, limit, start: start.value,
    });
    tasks.value = res.tasks || [];
    total.value = res.total || 0;
  } catch (e) {
    error.value = e.message || "Could not load ERP tasks";
  } finally {
    loading.value = false;
  }
}
function reload() {
  start.value = 0;
  load();
}
function page(dir) {
  start.value = Math.max(0, start.value + dir * limit);
  load();
}
onMounted(load);
</script>
