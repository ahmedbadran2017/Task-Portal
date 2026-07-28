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
        :label="priorityMeta.label"
        :color="priorityMeta.color"
        :bg="priorityMeta.bg"
        :ring="priorityMeta.ring"
        dot
      />
    </div>

    <p class="mt-2 text-sm font-medium text-ink-900 leading-snug line-clamp-2">
      {{ ticket.title }}
    </p>

    <div v-if="ticket.linked_label" class="mt-1.5">
      <span class="inline-flex items-center gap-1 text-[11px] text-ink-500 bg-ink-50 px-1.5 py-0.5 rounded">
        🔗 {{ ticket.linked_label }}
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
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Pill from "./Pill.vue";
import { PRIORITY_META, PORTAL_META } from "@/composables/useTickets";
import { relTime } from "@/composables/useApi";

const props = defineProps({ ticket: { type: Object, required: true } });
defineEmits(["open"]);

const priorityMeta = computed(
  () => PRIORITY_META[props.ticket.priority] || PRIORITY_META.Medium
);
const portalMeta = computed(() => PORTAL_META[props.ticket.source_portal] || PORTAL_META.Other);
const due = computed(() =>
  props.ticket.sla_deadline ? relTime(props.ticket.sla_deadline) : ""
);

function shortUser(u) {
  return String(u).split("@")[0];
}
</script>
