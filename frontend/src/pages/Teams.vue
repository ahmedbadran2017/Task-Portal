<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <p class="text-sm text-ink-500">
        Performance per department — resolution speed and SLA discipline, last
        <b>{{ days }}</b> days.
      </p>
      <div class="flex items-center gap-2">
        <div class="inline-flex rounded-xl border border-ink-200 overflow-hidden">
          <button
            class="px-3 py-1.5 text-xs font-semibold transition"
            :class="mode === 'departments' ? 'bg-brand-500 text-white' : 'bg-white text-ink-600 hover:bg-ink-50'"
            @click="mode = 'departments'; selected = ''; load()"
          >{{ t("Departments") }}</button>
          <button
            class="px-3 py-1.5 text-xs font-semibold transition"
            :class="mode === 'workspaces' ? 'bg-brand-500 text-white' : 'bg-white text-ink-600 hover:bg-ink-50'"
            @click="mode = 'workspaces'; selected = ''; load()"
          >{{ t("Workspaces") }}</button>
        </div>
        <button
          v-for="d in [7, 30, 90]"
          :key="d"
          class="px-3 py-1.5 rounded-full text-xs font-semibold border transition"
          :class="days === d ? 'bg-brand-50 border-brand-300 text-brand-700' : 'bg-white border-ink-200 text-ink-500 hover:border-ink-300'"
          @click="days = d; load()"
        >
          {{ d }}d
        </button>
      </div>
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">
      {{ error }}
    </div>

    <!-- department cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      <button
        v-for="d in rows"
        :key="d.key"
        class="card card-hover p-5 text-left"
        :class="selected === d.key ? '!border-brand-400 ring-2 ring-brand-200' : ''"
        @click="select(d.key)"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0 flex items-center gap-2">
            <span v-if="d.icon" class="w-7 h-7 rounded-lg grid place-items-center text-sm shrink-0"
                  :style="{ background: (d.color || '#78716c') + '22' }">{{ d.icon }}</span>
            <div class="text-sm font-bold text-ink-900 truncate">{{ d.key }}</div>
          </div>
          <span class="text-[11px] text-ink-400 shrink-0">{{ d.members }} {{ t("people") }}</span>
          <span
            v-if="d.breached"
            class="text-[10px] font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded shrink-0"
          >{{ d.breached }} SLA</span>
        </div>

        <div class="grid grid-cols-3 gap-2 mt-4 text-center">
          <div>
            <div class="text-xl font-bold text-ink-900 tabular-nums">{{ d.open }}</div>
            <div class="text-[10px] text-ink-400 uppercase tracking-wide">{{ t("Open") }}</div>
          </div>
          <div>
            <div class="text-xl font-bold text-emerald-600 tabular-nums">{{ d.resolved }}</div>
            <div class="text-[10px] text-ink-400 uppercase tracking-wide">{{ t("Resolved") }}</div>
          </div>
          <div>
            <div class="text-xl font-bold text-ink-700 tabular-nums">
              {{ d.avg_resolution_hours != null ? d.avg_resolution_hours + "h" : "—" }}
            </div>
            <div class="text-[10px] text-ink-400 uppercase tracking-wide">{{ t("Avg fix") }}</div>
          </div>
        </div>

        <!-- SLA compliance bar -->
        <div class="mt-4">
          <div class="flex items-center justify-between text-[11px] mb-1">
            <span class="text-ink-400">{{ t("SLA on-time") }}</span>
            <span class="font-semibold" :style="{ color: complianceColor(d.sla_compliance_pct) }">
              {{ d.sla_compliance_pct != null ? d.sla_compliance_pct + "%" : "no data" }}
            </span>
          </div>
          <div class="h-1.5 rounded-full bg-ink-100 overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :style="{
                width: (d.sla_compliance_pct || 0) + '%',
                background: complianceColor(d.sla_compliance_pct),
              }"
            />
          </div>
        </div>
      </button>
    </div>

    <p v-if="!rows.length && !loading" class="text-sm text-ink-400 text-center py-8">
      No department activity yet.
    </p>

    <!-- employee drill-down -->
    <div v-if="selected" class="card overflow-hidden">
      <div class="flex items-center justify-between px-5 pt-5 pb-3 gap-3 flex-wrap">
        <h3 class="text-sm font-bold text-ink-900">
          {{ selected }} — {{ t("people") }} ({{ days }}d)
        </h3>
        <button v-if="mode === 'departments'" class="btn-outline !py-1.5 text-xs" @click="viewTickets(selected)">
          {{ t("View team tickets →") }}
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-ink-50 text-ink-500 text-left text-xs uppercase tracking-wide">
              <th class="px-5 py-2.5 font-semibold">{{ t("Person") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Resolved") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Open now") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Breached") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Reported") }}</th>
              <th class="px-3 py-2.5 font-semibold">{{ t("Avg fix") }}</th>
              <th class="px-5 py-2.5 font-semibold">{{ t("SLA on-time") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in employees" :key="p.user" class="border-t border-ink-100">
              <td class="px-5 py-3">
                <span class="inline-flex items-center gap-2">
                  <span
                    class="w-7 h-7 rounded-full grid place-items-center text-[10px] font-bold text-white"
                    :style="{ background: avatarColor(p.user) }"
                  >{{ initials(p.full_name) }}</span>
                  <span class="font-medium text-ink-800">{{ p.full_name }}</span>
                </span>
              </td>
              <td class="px-3 py-3 tabular-nums font-semibold text-emerald-600">{{ p.resolved }}</td>
              <td class="px-3 py-3 tabular-nums">{{ p.open }}</td>
              <td class="px-3 py-3 tabular-nums">
                <span :class="p.breached ? 'text-rose-600 font-bold' : 'text-ink-400'">{{ p.breached }}</span>
              </td>
              <td class="px-3 py-3 tabular-nums text-ink-500">{{ p.reported }}</td>
              <td class="px-3 py-3 text-ink-600">
                {{ p.avg_resolution_hours != null ? p.avg_resolution_hours + "h" : "—" }}
              </td>
              <td class="px-5 py-3">
                <span
                  class="text-xs font-semibold"
                  :style="{ color: complianceColor(p.sla_compliance_pct) }"
                >
                  {{ p.sla_compliance_pct != null ? p.sla_compliance_pct + "%" : "—" }}
                </span>
              </td>
            </tr>
            <tr v-if="!employees.length && !empLoading">
              <td colspan="7" class="px-5 py-8 text-center text-ink-400">
                No linked employees found for this department.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p v-if="loading" class="text-sm text-ink-400 text-center py-4">{{ t("Loading scorecards…") }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "@/composables/useI18n";
import {
  getDepartmentScorecard, getEmployeeScorecard, getWorkspaceScorecard,
} from "@/composables/useTickets";

const router = useRouter();
const { t } = useI18n();
const mode = ref("departments");
const loading = ref(true);
const empLoading = ref(false);
const error = ref("");
const days = ref(30);
const departments = ref([]);
const wsRows = ref([]);
const employees = ref([]);
const selected = ref("");

// One unified card shape for both modes.
const rows = computed(() =>
  mode.value === "workspaces"
    ? wsRows.value.map((w) => ({ ...w, key: w.workspace }))
    : departments.value.map((d) => ({ ...d, key: d.department }))
);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    if (mode.value === "workspaces") {
      const res = await getWorkspaceScorecard(days.value);
      wsRows.value = res.workspaces || [];
    } else {
      const res = await getDepartmentScorecard(days.value);
      departments.value = res.departments || [];
    }
    if (selected.value) await loadEmployees(selected.value);
  } catch (e) {
    error.value = e.message || "Could not load scorecards";
  } finally {
    loading.value = false;
  }
}

async function select(dept) {
  selected.value = selected.value === dept ? "" : dept;
  if (selected.value) await loadEmployees(dept);
}

async function loadEmployees(dept) {
  empLoading.value = true;
  try {
    const res = mode.value === "workspaces"
      ? await getEmployeeScorecard(days.value, "", dept)
      : await getEmployeeScorecard(days.value, dept);
    employees.value = res.employees || [];
  } catch (e) {
    error.value = e.message || "Could not load employees";
  } finally {
    empLoading.value = false;
  }
}

function viewTickets(dept) {
  router.push({ path: "/tickets", query: { department: dept } });
}

function shortDept(d) {
  return String(d || "");
}
function complianceColor(pct) {
  if (pct == null) return "#a8a29e";
  if (pct >= 85) return "#059669";
  if (pct >= 60) return "#d97706";
  return "#e11d48";
}
const AVATAR_COLORS = ["#d45d3e", "#7c3aed", "#059669", "#2563eb", "#d97706", "#0891b2", "#9f1239"];
function avatarColor(u) {
  let hash = 0;
  for (const ch of String(u || "")) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}
function initials(n) {
  return String(n || "?")
    .split(/\s+/)
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

onMounted(load);
</script>
