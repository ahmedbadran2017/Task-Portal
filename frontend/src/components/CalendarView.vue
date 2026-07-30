<template>
  <div class="card overflow-hidden">
    <!-- month nav -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-ink-100">
      <button class="btn-ghost !px-2.5" @click="shift(-1)">‹</button>
      <div class="text-sm font-bold text-ink-900">{{ monthLabel }}</div>
      <div class="flex items-center gap-1">
        <button class="btn-outline !py-1 !px-2.5 text-xs" @click="goToday">{{ t("Today") }}</button>
        <button class="btn-ghost !px-2.5" @click="shift(1)">›</button>
      </div>
    </div>

    <!-- weekday header -->
    <div class="grid grid-cols-7 border-b border-ink-100 bg-ink-50">
      <div
        v-for="d in weekdays"
        :key="d"
        class="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wide text-ink-400 text-center"
      >{{ d }}</div>
    </div>

    <!-- grid -->
    <div class="grid grid-cols-7">
      <div
        v-for="cell in cells"
        :key="cell.key"
        class="min-h-[92px] border-b border-r border-ink-100 rtl:border-r-0 rtl:border-l p-1.5"
        :class="[
          cell.inMonth ? 'bg-white' : 'bg-ink-50/60',
          cell.isToday ? 'ring-2 ring-inset ring-brand-300' : '',
        ]"
      >
        <div
          class="text-[11px] font-semibold mb-1"
          :class="cell.isToday ? 'text-brand-600' : cell.inMonth ? 'text-ink-600' : 'text-ink-300'"
        >{{ cell.day }}</div>
        <div class="space-y-1">
          <button
            v-for="tk in (byDay[cell.key] || []).slice(0, 3)"
            :key="tk.name"
            class="w-full text-left rtl:text-right px-1.5 py-1 rounded-md text-[10px] font-medium leading-tight truncate block transition hover:opacity-80"
            :style="{ background: chipColor(tk) + '22', color: chipColor(tk) }"
            :title="tk.title"
            @click="ui.openTicket(tk.name)"
          >
            {{ tk.title }}
          </button>
          <div
            v-if="(byDay[cell.key] || []).length > 3"
            class="text-[10px] text-ink-400 px-1.5"
          >+{{ byDay[cell.key].length - 3 }}</div>
        </div>
      </div>
    </div>

    <p v-if="!loading && !Object.keys(byDay).length" class="text-center text-sm text-ink-400 py-6">
      {{ t("No tickets with a due date this month.") }}
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useUi } from "@/composables/useUi";
import { useI18n } from "@/composables/useI18n";
import { useWorkspaces } from "@/composables/useWorkspaces";
import { listTickets, PRIORITY_META } from "@/composables/useTickets";

const ui = useUi();
const { t, locale } = useI18n();
const { current: currentWsName, currentWs } = useWorkspaces();

const today = new Date();
const year = ref(today.getFullYear());
const month = ref(today.getMonth()); // 0-based
const tickets = ref([]);
const loading = ref(false);

const weekdays = computed(() =>
  locale.value === "ar"
    ? ["إثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت", "أحد"]
    : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
);

const monthLabel = computed(() =>
  new Date(year.value, month.value, 1).toLocaleDateString(
    locale.value === "ar" ? "ar-EG" : "en-GB",
    { month: "long", year: "numeric" }
  )
);

function iso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

// Monday-first 42-cell grid.
const cells = computed(() => {
  const first = new Date(year.value, month.value, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const start = new Date(year.value, month.value, 1 - startOffset);
  const out = [];
  const todayKey = iso(new Date());
  for (let i = 0; i < 42; i++) {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
    const key = iso(d);
    out.push({
      key,
      day: d.getDate(),
      inMonth: d.getMonth() === month.value,
      isToday: key === todayKey,
    });
  }
  return out;
});

const byDay = computed(() => {
  const g = {};
  for (const tk of tickets.value) {
    if (!tk.due_date) continue;
    (g[tk.due_date] = g[tk.due_date] || []).push(tk);
  }
  return g;
});

// Stage color inside a workspace; priority color in All mode.
function chipColor(tk) {
  const st = currentWs.value?.stages?.find((s) => s.stage_name === tk.stage);
  if (st) return st.color || "#78716c";
  return (PRIORITY_META[tk.priority] || PRIORITY_META.Medium).color;
}

function shift(dir) {
  const d = new Date(year.value, month.value + dir, 1);
  year.value = d.getFullYear();
  month.value = d.getMonth();
  load();
}

function goToday() {
  year.value = today.getFullYear();
  month.value = today.getMonth();
  load();
}

async function load() {
  loading.value = true;
  try {
    // Fetch the padded 6-week window so leading/trailing days populate too.
    const from = cells.value[0].key;
    const to = cells.value[41].key;
    const res = await listTickets({
      workspace: currentWsName.value || undefined,
      due_from: from,
      due_to: to,
      limit: 500,
      order_by: "due_date asc",
    });
    tickets.value = res.tickets || [];
  } catch {
    tickets.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(currentWsName, load);
watch(() => ui.state.rev, load);
</script>
