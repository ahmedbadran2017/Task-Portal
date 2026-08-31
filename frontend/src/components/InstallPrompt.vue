<template>
  <transition name="slide-up">
    <div
      v-if="visible"
      class="fixed inset-x-0 bottom-0 z-[70] p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]"
    >
      <div class="mx-auto max-w-md rounded-2xl bg-white shadow-2xl border border-ink-200 overflow-hidden">
        <div class="p-4">
          <div class="flex items-start gap-3">
            <img :src="iconSrc" alt="" class="w-11 h-11 rounded-xl shrink-0 shadow-sm" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-bold text-ink-900">{{ t("Install Task Hub") }}</p>
              <p class="text-xs text-ink-500 mt-0.5 leading-relaxed">
                {{ ios
                  ? t("Add it to your Home Screen to get notifications on this iPhone.")
                  : t("Install it for a full screen and notifications on your phone.") }}
              </p>
            </div>
            <button
              class="text-ink-300 hover:text-ink-600 shrink-0 -mt-1 -me-1 p-1"
              :aria-label="t('Not now')"
              @click="dismiss"
            >
              <NavIcon name="x" :size="14" />
            </button>
          </div>

          <!-- iOS has no install API — the only useful thing is directions. -->
          <ol v-if="ios" class="mt-3 space-y-1.5 text-xs text-ink-700 list-decimal ms-4">
            <li>
              {{ t("Tap") }}
              <span class="inline-flex items-center justify-center w-5 h-5 align-middle rounded border border-ink-300 mx-0.5">
                <NavIcon name="share-ios" :size="11" class="text-brand-600" />
              </span>
              {{ t("at the bottom of Safari") }}
            </li>
            <li>{{ t("Choose “Add to Home Screen”") }}</li>
            <li>{{ t("Open Task Hub from the new icon") }}</li>
          </ol>

          <div v-else class="mt-3 flex gap-2">
            <button class="btn-primary flex-1 !py-2 text-sm" :disabled="busy" @click="install">
              {{ busy ? t("Installing…") : t("Install") }}
            </button>
            <button class="btn-outline !py-2 text-sm" @click="dismiss">{{ t("Not now") }}</button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import NavIcon from "./NavIcon.vue";
import { useI18n } from "@/composables/useI18n";
import { isIOS } from "@/composables/usePush";
import { canShowBanner, snooze, promptInstall } from "@/composables/useInstall";

const { t } = useI18n();
// Bound rather than literal: a static src makes the bundler try to resolve a
// path that only exists once Frappe serves the app's public folder.
const iconSrc = import.meta.env.DEV
  ? "/icon-192.png"
  : "/assets/task_hub/icon-192.png";
const ios = isIOS();
const visible = ref(false);
const busy = ref(false);
let timer = null;

function dismiss() {
  snooze();
  visible.value = false;
}

async function install() {
  busy.value = true;
  try {
    await promptInstall();
  } finally {
    busy.value = false;
    visible.value = false;
  }
}

onMounted(() => {
  // Let the page paint and settle first. A banner that slides in over the very
  // first frame reads as an ad and gets dismissed reflexively.
  timer = setTimeout(() => {
    visible.value = canShowBanner.value;
  }, 2500);
});
onUnmounted(() => clearTimeout(timer));
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.28s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(120%);
  opacity: 0;
}
</style>
