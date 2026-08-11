<template>
  <div class="relative" ref="rootEl">
    <div
      class="input min-h-[38px] h-auto flex flex-wrap items-center gap-1.5 cursor-text py-1.5"
      :class="disabled ? 'opacity-60 pointer-events-none' : ''"
      @click="openList"
    >
      <span
        v-for="id in modelValue"
        :key="id"
        class="inline-flex items-center gap-1 pl-1 pr-1.5 py-0.5 rounded-full bg-brand-50 border border-brand-200 text-[11px] text-ink-800 max-w-full"
      >
        <span
          class="w-4 h-4 rounded-full grid place-items-center text-[8px] font-bold text-white shrink-0"
          :style="{ background: avatarColor(id) }"
        >{{ initials(label(id)) }}</span>
        <span class="truncate">{{ label(id) }}</span>
        <button
          type="button"
          class="text-ink-400 hover:text-rose-600 shrink-0"
          :aria-label="t('Remove')"
          @click.stop="remove(id)"
        >
          <NavIcon name="x" :size="9" />
        </button>
      </span>
      <span v-if="!modelValue.length" class="text-ink-400 text-sm">{{ placeholder || t("Add people…") }}</span>
      <NavIcon name="chevron-down" :size="12" class="text-ink-400 shrink-0 ms-auto" />
    </div>

    <div
      v-if="open"
      class="absolute z-30 mt-1 w-full bg-white border border-ink-200 rounded-xl shadow-lg overflow-hidden"
    >
      <div class="p-2 border-b border-ink-100">
        <input
          ref="searchEl"
          v-model="query"
          class="input !py-1.5"
          :placeholder="t('Search by name…')"
          @keydown.escape="open = false"
        />
      </div>
      <div class="max-h-52 overflow-y-auto scroll-thin">
        <button
          v-for="u in filtered"
          :key="u.name"
          type="button"
          class="w-full text-left rtl:text-right px-3 py-2 flex items-center gap-2 hover:bg-brand-50/60"
          :class="picked(u.name) ? 'bg-brand-50' : ''"
          @click="toggleUser(u.name)"
        >
          <span
            class="w-6 h-6 rounded-full grid place-items-center text-[10px] font-bold text-white shrink-0"
            :style="{ background: avatarColor(u.name) }"
          >{{ initials(u.full_name || u.name) }}</span>
          <span class="min-w-0 flex-1">
            <span class="block text-sm text-ink-800 truncate">{{ u.full_name || u.name }}</span>
            <span class="block text-[10px] text-ink-400 truncate">{{ u.name }}</span>
          </span>
          <!-- inherited members can't be unpicked here; they come from the department -->
          <span v-if="inherited.includes(u.name)" class="text-[10px] text-ink-400 shrink-0">
            {{ t("from department") }}
          </span>
          <NavIcon v-else-if="picked(u.name)" name="check" :size="12" class="text-brand-600 shrink-0" />
        </button>
        <p v-if="!filtered.length" class="px-3 py-3 text-xs text-ink-400">{{ t("No one matches.") }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// Multi-select people picker. Exists because a workspace's membership can't
// always come from an ERPNext department — some real teams (Media Buying) have
// no employees filed under them, so the department link resolves to nobody.
import { ref, computed, nextTick, onMounted, onUnmounted } from "vue";
import { useI18n } from "@/composables/useI18n";
import NavIcon from "./NavIcon.vue";

const { t } = useI18n();

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  users: { type: Array, default: () => [] }, // [{name, full_name}]
  inherited: { type: Array, default: () => [] }, // already members via department
  placeholder: { type: String, default: "" },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const open = ref(false);
const query = ref("");
const rootEl = ref(null);
const searchEl = ref(null);

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.users;
  return props.users.filter(
    (u) =>
      (u.full_name || "").toLowerCase().includes(q) ||
      u.name.toLowerCase().includes(q)
  );
});

function label(id) {
  const u = props.users.find((x) => x.name === id);
  return u ? u.full_name || u.name : String(id).split("@")[0];
}
function picked(id) {
  return props.modelValue.includes(id) || props.inherited.includes(id);
}
function toggleUser(id) {
  // Department-inherited people are already in; toggling them here would be a
  // no-op that reads as a broken checkbox.
  if (props.inherited.includes(id)) return;
  emit(
    "update:modelValue",
    props.modelValue.includes(id)
      ? props.modelValue.filter((x) => x !== id)
      : [...props.modelValue, id]
  );
}
function remove(id) {
  emit("update:modelValue", props.modelValue.filter((x) => x !== id));
}

async function openList() {
  if (open.value) return;
  open.value = true;
  query.value = "";
  await nextTick();
  searchEl.value?.focus();
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
