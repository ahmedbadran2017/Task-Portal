<template>
  <div class="relative" ref="rootEl">
    <button
      type="button"
      class="input flex items-center justify-between gap-2 text-left"
      :disabled="disabled"
      @click="toggle"
    >
      <span v-if="selectedLabel" class="flex items-center gap-2 min-w-0">
        <span
          class="w-5 h-5 rounded-full grid place-items-center text-[9px] font-bold text-white shrink-0"
          :style="{ background: avatarColor(modelValue) }"
        >{{ initials(selectedLabel) }}</span>
        <span class="truncate">{{ selectedLabel }}</span>
      </span>
      <span v-else class="text-ink-400">— Unassigned —</span>
      <span class="text-ink-400 text-xs shrink-0">▾</span>
    </button>

    <div
      v-if="open"
      class="absolute z-30 mt-1 w-full bg-white border border-ink-200 rounded-xl shadow-lg overflow-hidden"
    >
      <div class="p-2 border-b border-ink-100">
        <input
          ref="searchEl"
          v-model="query"
          class="input !py-1.5"
          placeholder="Search by name…"
          @keydown.escape="open = false"
        />
      </div>
      <div class="max-h-52 overflow-y-auto scroll-thin">
        <button
          type="button"
          class="w-full text-left px-3 py-2 text-sm text-ink-500 hover:bg-ink-50"
          @click="pick('')"
        >
          — Unassigned —
        </button>
        <button
          v-for="u in filtered"
          :key="u.name"
          type="button"
          class="w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-brand-50/60"
          :class="u.name === modelValue ? 'bg-brand-50' : ''"
          @click="pick(u.name)"
        >
          <span
            class="w-6 h-6 rounded-full grid place-items-center text-[10px] font-bold text-white shrink-0"
            :style="{ background: avatarColor(u.name) }"
          >{{ initials(u.full_name || u.name) }}</span>
          <span class="min-w-0">
            <span class="block text-sm text-ink-800 truncate">{{ u.full_name || u.name }}</span>
            <span class="block text-[10px] text-ink-400 truncate">{{ u.name }}</span>
          </span>
        </button>
        <p v-if="!filtered.length" class="px-3 py-3 text-xs text-ink-400">No one matches.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  users: { type: Array, default: () => [] }, // [{name, full_name}]
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const open = ref(false);
const query = ref("");
const rootEl = ref(null);
const searchEl = ref(null);

const selectedLabel = computed(() => {
  if (!props.modelValue) return "";
  const u = props.users.find((x) => x.name === props.modelValue);
  return u ? u.full_name || u.name : props.modelValue.split("@")[0];
});

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.users;
  return props.users.filter(
    (u) =>
      (u.full_name || "").toLowerCase().includes(q) ||
      u.name.toLowerCase().includes(q)
  );
});

async function toggle() {
  open.value = !open.value;
  if (open.value) {
    query.value = "";
    await nextTick();
    searchEl.value?.focus();
  }
}

function pick(name) {
  emit("update:modelValue", name);
  open.value = false;
}

function onDocClick(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) open.value = false;
}
onMounted(() => document.addEventListener("click", onDocClick));
onUnmounted(() => document.removeEventListener("click", onDocClick));

const AVATAR_COLORS = ["#d45d3e", "#7c3aed", "#059669", "#2563eb", "#d97706", "#0891b2", "#9f1239"];
function avatarColor(u) {
  let hash = 0;
  for (const ch of String(u || "")) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}
function initials(n) {
  return String(n || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
</script>
