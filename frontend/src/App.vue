<template>
  <div class="min-h-screen text-ink-900">
    <div class="brand-hairline fixed top-0 inset-x-0 z-[60]" />
    <div class="min-h-screen flex">
    <!-- Sidebar -->
    <aside
      class="hidden md:flex flex-col w-60 shrink-0 bg-white border-r border-ink-200 h-screen sticky top-0"
    >
      <div class="px-5 py-5 border-b border-ink-100">
        <img :src="logoSrc" alt="Justyol" class="h-5 w-auto" />
        <div class="text-[11px] font-bold text-brand-600 mt-1.5 tracking-widest uppercase">
          Task Hub
        </div>
      </div>

      <div class="px-3 pt-3">
        <WorkspaceSwitcher />
      </div>

      <nav class="flex-1 px-3 py-4 space-y-1">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 hover:translate-x-0.5 rtl:hover:-translate-x-0.5"
          :class="
            isActive(item.to)
              ? 'bg-brand-50 text-brand-700'
              : 'text-ink-500 hover:bg-ink-50 hover:text-ink-800'
          "
        >
          <span
            v-if="isActive(item.to)"
            class="absolute left-0 rtl:left-auto rtl:right-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r-full rtl:rounded-r-none rtl:rounded-l-full bg-brand-500"
          />
          <span
            class="w-7 h-7 grid place-items-center rounded-lg"
            :class="isActive(item.to) ? 'bg-brand-100 text-brand-700' : 'bg-ink-100 text-ink-500'"
          ><NavIcon :name="item.icon" :size="15" /></span>
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
          <img :src="logoSrc" alt="Justyol" class="h-4 w-auto" />
          <span class="text-[10px] font-bold text-brand-600 tracking-widest uppercase mt-0.5">
            {{ currentTitle }}
          </span>
        </div>

        <div class="hidden md:block text-sm font-semibold text-ink-700">
          {{ currentTitle }}
        </div>

        <div class="flex items-center gap-1.5">
          <!-- language toggle — EN | ع | FR, follows the user's ERPNext language until changed -->
          <div class="inline-flex rounded-lg border border-ink-200 overflow-hidden mr-1 rtl:mr-0 rtl:ml-1">
            <button
              v-for="l in LOCALES"
              :key="l.code"
              :title="l.name"
              class="px-2 py-1 text-[11px] font-bold transition-colors"
              :class="locale === l.code ? 'bg-brand-500 text-white' : 'bg-white text-ink-500 hover:bg-ink-50'"
              @click="setLocale(l.code)"
            >
              {{ l.label }}
            </button>
          </div>
          <NotificationBell />
          <button class="btn-primary" @click="ui.openCreate()">
          <span class="text-base leading-none">+</span>
          <span class="hidden sm:inline">{{ t("New Ticket") }}</span>
          <span class="sm:hidden">{{ t("New") }}</span>
          </button>
        </div>
      </header>

      <main class="flex-1 p-4 sm:p-6 pb-24 md:pb-6">
        <div class="md:hidden mb-3">
          <WorkspaceSwitcher />
        </div>
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>

      <!-- mobile bottom tab bar — app-like navigation -->
      <nav
        class="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur border-t border-ink-200 flex"
        style="padding-bottom: env(safe-area-inset-bottom)"
      >
        <router-link
          v-for="item in nav.filter((i) => !i.desktopOnly)"
          :key="item.to"
          :to="item.to"
          class="flex-1 flex flex-col items-center gap-0.5 pt-2 pb-1.5 min-h-[56px] transition-colors"
          :class="isActive(item.to) ? 'text-brand-600' : 'text-ink-400'"
        >
          <span
            class="px-3 py-1 rounded-full transition-colors"
            :class="isActive(item.to) ? 'bg-brand-100/80' : ''"
          ><NavIcon :name="item.icon" :size="19" /></span>
          <span class="text-[10px] font-semibold">{{ item.short || item.label }}</span>
        </router-link>
      </nav>
    </div>

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
import NavIcon from "@/components/NavIcon.vue";
import NotificationBell from "@/components/NotificationBell.vue";
import WorkspaceSwitcher from "@/components/WorkspaceSwitcher.vue";
import { useUi } from "@/composables/useUi";
import { useI18n } from "@/composables/useI18n";
import { COMPANY, isManager } from "@/composables/useApi";

const ui = useUi();
const route = useRoute();
const { t, locale, setLocale, LOCALES } = useI18n();

// Served by Frappe from the app's public/ dir in production; the dev server
// serves the copy in frontend/public/ instead (bound, not static-imported, so
// vite's single-bundle assetFileNames pattern never tries to emit it).
const logoSrc = import.meta.env.DEV
  ? "/justyol-logo.png"
  : "/assets/task_hub/justyol-logo.png";

// Teams (scorecards) is management-only — everyone else's hub is scoped to
// their own tickets, so a performance page would be empty noise.
const nav = computed(() =>
  [
    { to: "/dashboard", label: t("Dashboard"), icon: "dashboard" },
    { to: "/my", label: t("My Work"), icon: "user" },
    { to: "/requests", label: t("Requests"), icon: "send" },
    { to: "/board", label: t("Board"), icon: "board" },
    { to: "/tickets", label: t("All Tickets"), short: t("Tickets"), icon: "list" },
    { to: "/teams", label: t("Teams"), icon: "users", managerOnly: true, desktopOnly: true },
    { to: "/command", label: t("Command"), icon: "gauge", managerOnly: true, desktopOnly: true },
    { to: "/settings", label: t("Settings"), icon: "settings" },
  ].filter((i) => !i.managerOnly || isManager())
);

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
const currentTitle = computed(() => nav.value.find((n) => isActive(n.to))?.label || t("Task Hub"));
</script>
