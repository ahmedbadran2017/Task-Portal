<template>
  <div class="min-h-screen flex bg-ink-50 text-ink-900">
    <!-- Sidebar -->
    <aside
      class="hidden md:flex flex-col w-60 shrink-0 bg-white border-r border-ink-200 h-screen sticky top-0"
    >
      <div class="px-5 py-5 flex items-center gap-2.5 border-b border-ink-100">
        <div
          class="w-8 h-8 rounded-lg bg-brand-500 text-white grid place-items-center font-bold"
        >
          T
        </div>
        <div>
          <div class="text-sm font-bold leading-none">Task Hub</div>
          <div class="text-[11px] text-ink-400 mt-0.5">Justyol</div>
        </div>
      </div>

      <nav class="flex-1 px-3 py-4 space-y-1">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition"
          :class="
            isActive(item.to)
              ? 'bg-brand-50 text-brand-700'
              : 'text-ink-600 hover:bg-ink-50'
          "
        >
          <span>{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </nav>

      <div class="px-4 py-4 border-t border-ink-100">
        <div class="flex items-center gap-2.5">
          <div
            class="w-8 h-8 rounded-full bg-ink-200 grid place-items-center text-xs font-semibold text-ink-600"
          >
            {{ initials }}
          </div>
          <div class="min-w-0">
            <div class="text-xs font-semibold truncate">{{ fullName }}</div>
            <div class="text-[11px] text-ink-400 truncate">{{ company }}</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex-1 min-w-0 flex flex-col">
      <header
        class="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-ink-200 px-4 sm:px-6 py-3 flex items-center justify-between gap-3"
      >
        <div class="flex items-center gap-2 md:hidden">
          <div class="w-7 h-7 rounded-md bg-brand-500 text-white grid place-items-center font-bold text-sm">
            T
          </div>
          <span class="font-bold text-sm">Task Hub</span>
        </div>

        <!-- mobile nav -->
        <nav class="flex md:hidden items-center gap-1">
          <router-link
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="px-2.5 py-1.5 rounded-lg text-xs font-medium"
            :class="isActive(item.to) ? 'bg-brand-50 text-brand-700' : 'text-ink-500'"
          >
            {{ item.label }}
          </router-link>
        </nav>

        <div class="hidden md:block text-sm font-semibold text-ink-700">
          {{ currentTitle }}
        </div>

        <button class="btn-primary" @click="ui.openCreate()">
          <span class="text-base leading-none">+</span> New Ticket
        </button>
      </header>

      <main class="flex-1 p-4 sm:p-6">
        <router-view />
      </main>
    </div>

    <CreateTicketModal />
    <TicketDrawer />
    <Toaster />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import CreateTicketModal from "@/components/CreateTicketModal.vue";
import TicketDrawer from "@/components/TicketDrawer.vue";
import Toaster from "@/components/Toaster.vue";
import { useUi } from "@/composables/useUi";
import { COMPANY } from "@/composables/useApi";

const ui = useUi();
const route = useRoute();

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: "▤" },
  { to: "/board", label: "Board", icon: "▦" },
  { to: "/tickets", label: "All Tickets", icon: "☰" },
];

const fullName = (typeof window !== "undefined" && window.full_name) || "User";
const company = COMPANY;
const initials = computed(() =>
  String(fullName)
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()
);

function isActive(to) {
  return route.path.startsWith(to);
}
const currentTitle = computed(() => nav.find((n) => isActive(n.to))?.label || "Task Hub");
</script>
