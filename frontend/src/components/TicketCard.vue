<template>
  <div
    class="card p-3.5 hover:shadow-md hover:border-ink-300 transition cursor-pointer group"
    @click="$emit('open', ticket.name)"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-center gap-1.5 min-w-0">
        <span
          class="w-2 h-2 rounded-full shrink-0"
          :style="{ background: portalMeta.color }"
          :title="ticket.source_portal"
        />
        <span class="text-[11px] font-mono text-ink-400 truncate">{{ ticket.name }}</span>
      </div>
      <Pill
        :label="t(ticket.priority)"
        :color="priorityMeta.color"
        :bg="priorityMeta.bg"
        :ring="priorityMeta.ring"
        dot
      />
    </div>

    <p class="mt-2 text-sm font-medium text-ink-900 leading-snug line-clamp-2">
      {{ ticket.title }}
    </p>

    <div v-if="ticket.blocked_by" class="mt-1.5">
      <span class="inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded text-rose-700 bg-rose-50 font-semibold">
        <NavIcon name="ban" :size="10" /> {{ ticket.blocked_by }}
      </span>
    </div>
    <div v-if="ticket.due_date" class="mt-1.5">
      <span class="inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded"
            :class="dueOver ? 'text-rose-700 bg-rose-50 font-semibold' : 'text-ink-500 bg-ink-50'">
        <NavIcon name="calendar" :size="10" /> {{ fmtDate(ticket.due_date) }}
      </span>
    </div>
    <div v-if="ticket.linked_label" class="mt-1.5">
      <span class="inline-flex items-center gap-1 text-[11px] text-ink-500 bg-ink-50 px-1.5 py-0.5 rounded">
        <NavIcon name="link" :size="10" /> {{ ticket.linked_label }}
      </span>
    </div>

    <div class="mt-3 flex items-center justify-between gap-2">
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="text-[11px] font-medium" :style="{ color: portalMeta.color }">
          {{ ticket.source_portal }}
        </span>
        <span v-if="ticket.assigned_to" class="text-[11px] text-ink-400 truncate">
          · {{ shortUser(ticket.assigned_to) }}
        </span>
      </div>
      <span
        v-if="ticket.sla_breached"
        class="text-[10px] font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded"
        >SLA</span
      >
      <span v-else class="text-[11px] text-ink-400 whitespace-nowrap">{{ due }}</span>
      <!-- touch devices can't drag — one tap advances the column -->
      <button
        v-if="advance"
        class="md:hidden shrink-0 w-7 h-7 grid place-items-center rounded-lg bg-brand-50 text-brand-600 font-bold"
        :title="advance"
        @click.stop="$emit('advance', ticket)"
      >→</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Pill from "./Pill.vue";
import NavIcon from "./NavIcon.vue";
import { useI18n } from "@/composables/useI18n";
import { PRIORITY_META, PORTAL_META } from "@/composables/useTickets";
import { relTime, fmtDate } from "@/composables/useApi";

const { t } = useI18n();

const props = defineProps({
  ticket: { type: Object, required: true },
  // Next column name — shows the one-tap advance button on touch screens.
  advance: { type: String, default: "" },
});
defineEmits(["open", "advance"]);

const priorityMeta = computed(
  () => PRIORITY_META[props.ticket.priority] || PRIORITY_META.Medium
);
const portalMeta = computed(() => PORTAL_META[props.ticket.source_portal] || PORTAL_META.Other);
const due = computed(() =>
  props.ticket.sla_deadline ? relTime(props.ticket.sla_deadline) : ""
);
const dueOver = computed(() => {
  if (!props.ticket.due_date) return false;
  return new Date(props.ticket.due_date + "T23:59:59").getTime() < Date.now();
});

function shortUser(u) {
  return String(u).split("@")[0];
}
</script>
