<template>
  <div class="relative" ref="rootEl" v-if="workspaces.length">
    <button
      class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-ink-200 bg-white hover:border-ink-300 transition text-left"
      @click="open = !open"
    >
      <span
        class="w-7 h-7 rounded-lg grid place-items-center text-sm shrink-0"
        :style="{ background: (currentWs?.color || '#78716c') + '22' }"
      >{{ currentWs?.icon || "🗂️" }}</span>
      <span class="min-w-0 flex-1">
        <span class="block text-sm font-bold text-ink-900 truncate">
          {{ currentWs ? currentWs.name : t("All workspaces") }}
        </span>
        <span class="block text-[10px] text-ink-400">
          {{ currentWs ? currentWs.open_count + " " + t("open") : workspaces.length + " workspaces" }}
        </span>
      </span>
      <NavIcon name="chevron-down" :size="12" class="text-ink-400" />
    </button>

    <div
      v-if="open"
      class="absolute z-40 mt-1.5 w-full min-w-[240px] bg-white border border-ink-200 rounded-xl shadow-xl overflow-hidden"
    >
      <button
        class="w-full text-left px-3 py-2.5 flex items-center gap-2.5 hover:bg-ink-50 transition"
        :class="!current ? 'bg-brand-50/60' : ''"
        @click="pick('')"
      >
        <span class="w-7 h-7 rounded-lg grid place-items-center bg-ink-100 text-ink-500"><NavIcon name="globe" :size="14" /></span>
        <span class="text-sm font-medium text-ink-800">{{ t("All workspaces") }}</span>
      </button>
      <button
        v-for="w in workspaces"
        :key="w.name"
        class="w-full text-left px-3 py-2.5 flex items-center gap-2.5 hover:bg-ink-50 transition"
        :class="current === w.name ? 'bg-brand-50/60' : ''"
        @click="pick(w.name)"
      >
        <span
          class="w-7 h-7 rounded-lg grid place-items-center text-sm shrink-0"
          :style="{ background: w.color + '22' }"
        >{{ w.icon }}</span>
        <span class="min-w-0 flex-1">
          <span class="block text-sm font-medium text-ink-800 truncate">{{ w.name }}</span>
          <span class="block text-[10px] text-ink-400">
            {{ w.member_count }} {{ t("people") }} · {{ w.open_count }} {{ t("open") }}
          </span>
        </span>
        <span
          v-if="w.is_member"
          class="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"
          title="You're a member"
        />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import NavIcon from "./NavIcon.vue";
import { useWorkspaces } from "@/composables/useWorkspaces";
import { useI18n } from "@/composables/useI18n";
import { useUi } from "@/composables/useUi";

const { workspaces, current, currentWs, setCurrent } = useWorkspaces();
const { t } = useI18n();
const ui = useUi();
const open = ref(false);
const rootEl = ref(null);

function pick(name) {
  setCurrent(name);
  open.value = false;
  ui.bump(); // boards/lists listening on rev refetch with the new context
}

function onDocClick(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) open.value = false;
}
onMounted(() => document.addEventListener("click", onDocClick));
onUnmounted(() => document.removeEventListener("click", onDocClick));
</script>
