<template>
  <div class="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 w-80 max-w-[calc(100vw-2.5rem)]">
    <transition-group name="toast">
      <div
        v-for="t in toast.items"
        :key="t.id"
        class="flex items-start gap-3 px-4 py-3 rounded-xl shadow-lg text-sm text-white cursor-pointer"
        :style="{ background: bg(t.tone) }"
        @click="toast.dismiss(t.id)"
      >
        <span class="mt-0.5">{{ icon(t.tone) }}</span>
        <span class="flex-1">{{ t.message }}</span>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useToast } from "@/composables/useToast";

const toast = useToast();

function bg(tone) {
  return { success: "#059669", error: "#dc2626", info: "#1f2937" }[tone] || "#1f2937";
}
function icon(tone) {
  return { success: "✓", error: "✕", info: "ℹ" }[tone] || "ℹ";
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
