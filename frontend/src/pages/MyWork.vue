<template>
  <div class="max-w-3xl mx-auto space-y-5">
    <!-- Work you asked for is still your work — a ticket you raised and handed
         off used to disappear from this page entirely. -->
    <div class="flex items-center gap-1 p-1 rounded-xl bg-ink-100 w-fit">
      <button
        v-for="s in SCOPES"
        :key="s.key"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition"
        :class="scope === s.key ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500 hover:text-ink-700'"
        @click="setScope(s.key)"
      >
        {{ t(s.label) }}
      </button>
    </div>

    <!-- headline chips -->
    <div class="grid grid-cols-3 gap-3">
      <div class="card p-3.5 text-center">
        <div class="text-2xl font-bold text-ink-900 tabular-nums">{{ tickets.length }}</div>
        <div class="text-[11px] text-ink-400 uppercase tracking-wide">{{ t("Open") }}</div>
      </div>
      <div class="card p-3.5 text-center">
        <div class="text-2xl font-bold tabular-nums" :class="breached.length ? 'text-rose-600' : 'text-ink-900'">
          {{ breached.length }}
        </div>
        <div class="text-[11px] text-ink-400 uppercase tracking-wide">{{ t("SLA breached") }}</div>
      </div>
      <div class="card p-3.5 text-center">
        <div class="text-2xl font-bold text-amber-600 tabular-nums">{{ dueSoon.length }}</div>
        <div class="text-[11px] text-ink-400 uppercase tracking-wide">≤ 24h</div>
      </div>
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">{{ error }}</div>

    <Section v-if="breached.length" icon="alarm" :title="t('SLA breached')" tone="#e11d48">
      <Row v-for="tk in breached" :key="tk.name" :tk="tk" :me="me" @open="ui.openTicket" />
    </Section>

    <Section v-if="dueSoon.length" icon="hourglass" :title="t('Due') + ' ≤ 24h'" tone="#d97706">
      <Row v-for="tk in dueSoon" :key="tk.name" :tk="tk" :me="me" @open="ui.openTicket" />
    </Section>

    <Section v-if="rest.length" icon="list" :title="t('All Tickets')" tone="#78716c">
      <Row v-for="tk in rest" :key="tk.name" :tk="tk" :me="me" @open="ui.openTicket" />
    </Section>

    <div v-if="!tickets.length && !loading" class="card p-10 text-center">
      <NavIcon name="check-circle" :size="32" class="inline-block mb-3 text-emerald-500" />
      <p class="text-sm text-ink-500">{{ t("No open tickets — all clear") }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, h } from "vue";
import Pill from "@/components/Pill.vue";
import NavIcon from "@/components/NavIcon.vue";
import { useUi } from "@/composables/useUi";
import { useI18n } from "@/composables/useI18n";
import { listTickets, PRIORITY_META } from "@/composables/useTickets";
import { relTime, parseServerDate, currentUserId } from "@/composables/useApi";

const ui = useUi();
const { t } = useI18n();
const loading = ref(true);
const error = ref("");
const tickets = ref([]);
const me = currentUserId();

const SCOPES = [
  { key: "involved", label: "Everything of mine" },
  { key: "assigned", label: "Assigned to me" },
  { key: "reported", label: "Raised by me" },
];
// Survives navigation, so the page doesn't snap back on every visit.
const scope = ref(localStorage.getItem("th_mywork_scope") || "involved");

function setScope(k) {
  scope.value = k;
  localStorage.setItem("th_mywork_scope", k);
  load();
}

const now = () => Date.now();
const H24 = 24 * 3600 * 1000;

function deadlineMs(tk) {
  // Site-timezone aware, so "due within 24h" means the same thing to a
  // Morocco browser as it does on the server.
  const dl = tk.sla_deadline ? parseServerDate(tk.sla_deadline) : null;
  const d = dl ? dl.getTime() : Infinity;
  const dueDay = tk.due_date ? parseServerDate(tk.due_date) : null;
  const due = dueDay ? dueDay.getTime() + 86399000 : Infinity;
  return Math.min(d, due);
}

const breached = computed(() => tickets.value.filter((tk) => tk.sla_breached));
const dueSoon = computed(() =>
  tickets.value.filter((tk) => !tk.sla_breached && deadlineMs(tk) - now() < H24)
);
const rest = computed(() =>
  tickets.value.filter((tk) => !tk.sla_breached && deadlineMs(tk) - now() >= H24)
);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const res = await listTickets({
      mine: scope.value, limit: 200, order_by: "sla_deadline asc",
    });
    tickets.value = (res.tickets || []).filter((tk) =>
      ["Open", "In Progress", "In Review"].includes(tk.status)
    );
  } catch (e) {
    error.value = e.message || "Could not load your work";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(() => ui.state.rev, load);

// section wrapper + compact row
const Section = (props, { slots }) =>
  h("div", { class: "card overflow-hidden" }, [
    h("div", {
      class: "px-4 py-2.5 text-xs font-bold uppercase tracking-wide border-b border-ink-100 flex items-center gap-1.5",
      style: { color: props.tone },
    }, [props.icon ? h(NavIcon, { name: props.icon, size: 13 }) : null, props.title]),
    h("div", {}, slots.default?.()),
  ]);
Section.props = ["title", "tone", "icon"];

const Row = (props, { emit }) => {
  // In the mixed view "am I doing this or waiting on it?" is the first
  // question, so the row answers it before you open the ticket.
  const waiting = props.me && props.tk.assigned_to !== props.me;
  return h("button", {
    class: "w-full text-left rtl:text-right px-4 py-3 flex items-center gap-3 border-b border-ink-50 hover:bg-ink-50 transition",
    onClick: () => emit("open", props.tk.name),
  }, [
    h("span", {
      class: "w-1.5 h-8 rounded-full shrink-0",
      style: { background: (PRIORITY_META[props.tk.priority] || {}).color || "#a8a29e" },
    }),
    h("span", { class: "min-w-0 flex-1" }, [
      h("span", { class: "block text-sm font-medium text-ink-900 truncate" }, props.tk.title),
      h("span", { class: "block text-[11px] text-ink-400 truncate" },
        [props.tk.name, props.tk.source_portal,
         waiting ? t("waiting on {0}", shortUser(props.tk.assigned_to)) : null]
          .filter(Boolean).join(" · ")),
    ]),
    h("span", { class: "text-[11px] text-ink-400 shrink-0" },
      props.tk.sla_deadline ? relTime(props.tk.sla_deadline) : ""),
  ]);
};
Row.props = ["tk", "me"];
Row.emits = ["open"];

function shortUser(u) {
  return u ? String(u).split("@")[0] : t("nobody");
}
</script>
