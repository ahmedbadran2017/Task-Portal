<template>
  <div class="max-w-md mx-auto card p-10 text-center mt-10">
    <NavIcon name="circle-dashed" :size="32" class="inline-block mb-3 text-ink-300" />
    <h2 class="text-lg font-bold text-ink-900 mb-1">{{ t("Page not found") }}</h2>
    <p class="text-sm text-ink-400 mb-5 font-mono break-all">{{ route.fullPath }}</p>
    <router-link to="/dashboard" class="btn-primary inline-flex">
      {{ t("Back to dashboard") }}
    </router-link>
  </div>
</template>

<script setup>
import { useRoute } from "vue-router";
import NavIcon from "@/components/NavIcon.vue";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const route = useRoute();
</script>
