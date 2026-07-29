<template>
  <div class="relative" ref="rootEl">
    <button
      class="relative w-9 h-9 grid place-items-center rounded-xl text-ink-500 hover:bg-ink-100 transition"
      title="Notifications"
      @click="toggle"
    >
      <NavIcon name="bell" :size="18" />
      <span
        v-if="unread"
        class="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-brand-500 text-white text-[9px] font-bold grid place-items-center"
      >{{ unread > 99 ? "99+" : unread }}</span>
    </button>

    <div
      v-if="open"
      class="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-white border border-ink-200 rounded-2xl shadow-xl z-50 overflow-hidden"
    >
      <div class="flex items-center justify-between px-4 py-3 border-b border-ink-100">
        <span class="text-sm font-bold text-ink-900">Notifications</span>
        <button
          v-if="unread"
          class="text-[11px] font-semibold text-brand-600 hover:underline"
          @click="markAll"
        >
          Mark all read
        </button>
      </div>
      <div class="max-h-[60vh] overflow-y-auto scroll-thin">
        <button
          v-for="n in items"
          :key="n.name"
          class="w-full text-left px-4 py-3 flex gap-2.5 border-b border-ink-50 hover:bg-ink-50 transition"
          :class="n.seen ? 'opacity-60' : ''"
          @click="openItem(n)"
        >
          <span
            class="w-7 h-7 rounded-full grid place-items-center text-xs shrink-0 mt-0.5 font-bold text-white"
            :style="{ background: meta(n.ntype).color }"
          >{{ meta(n.ntype).icon }}</span>
          <span class="min-w-0">
            <span class="block text-[13px] text-ink-800 leading-snug line-clamp-2">{{ n.message }}</span>
            <span class="block text-[11px] text-ink-400 mt-0.5">
              {{ n.ticket ? n.ticket + " · " : "" }}{{ relTime(n.creation) }}
            </span>
          </span>
          <span v-if="!n.seen" class="w-2 h-2 rounded-full bg-brand-500 shrink-0 mt-2 ml-auto" />
        </button>
        <p v-if="!items.length" class="px-4 py-8 text-center text-sm text-ink-400">
          Nothing yet — you're all caught up 🎉
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import NavIcon from "./NavIcon.vue";
import { useUi } from "@/composables/useUi";
import { myNotifications, markSeen, NOTIF_META } from "@/composables/useTickets";
import { relTime } from "@/composables/useApi";

const ui = useUi();
const open = ref(false);
const items = ref([]);
const unread = ref(0);
const rootEl = ref(null);
let timer = null;

function meta(t) {
  return NOTIF_META[t] || { icon: "•", color: "#78716c" };
}

async function load() {
  try {
    const res = await myNotifications();
    items.value = res.notifications || [];
    unread.value = res.unread || 0;
  } catch {
    /* not installed / offline — bell stays quiet */
  }
}

function toggle() {
  open.value = !open.value;
  if (open.value) load();
}

async function openItem(n) {
  if (!n.seen) {
    n.seen = 1;
    unread.value = Math.max(0, unread.value - 1);
    markSeen(n.name).catch(() => {});
  }
  if (n.ticket) {
    ui.openTicket(n.ticket);
    open.value = false;
  }
}

async function markAll() {
  try {
    const res = await markSeen();
    unread.value = res.unread || 0;
    items.value = items.value.map((n) => ({ ...n, seen: 1 }));
  } catch {}
}

function onDocClick(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) open.value = false;
}

onMounted(() => {
  load();
  timer = setInterval(load, 45000);
  document.addEventListener("click", onDocClick);
});
onUnmounted(() => {
  timer && clearInterval(timer);
  document.removeEventListener("click", onDocClick);
});
</script>
