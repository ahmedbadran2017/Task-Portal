<template>
  <div v-if="enabled" class="mt-2">
    <button
      v-if="!preview"
      type="button"
      class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition
             border-ink-200 bg-white text-ink-600 hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50
             disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="busy || !hasText"
      @click="polish"
    >
      <span v-if="busy" class="animate-pulse">✨ {{ t("Rewriting…") }}</span>
      <span v-else>✨ {{ t("Rewrite in English") }}</span>
    </button>

    <div
      v-else
      class="rounded-xl border border-brand-200 bg-brand-50/60 p-3 space-y-2 fade-up"
    >
      <div class="flex items-center gap-1.5 text-[11px] font-bold text-brand-700 uppercase tracking-wide">
        ✨ {{ t("AI suggestion") }}
      </div>
      <div class="text-sm text-ink-800 whitespace-pre-wrap leading-relaxed">{{ preview }}</div>
      <div class="flex gap-2 pt-1">
        <button type="button" class="btn-primary !py-1.5 !px-3 text-xs" @click="apply">
          {{ t("Use suggestion") }}
        </button>
        <button type="button" class="btn-outline !py-1.5 !px-3 text-xs" @click="preview = ''">
          {{ t("Keep original") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
// "✨ Rewrite in English" — sits under a description textarea. Sends the text
// to task_hub.api.ai.polish_description, shows the suggestion as a preview,
// and only replaces the text when the user explicitly accepts it.
import { ref, computed, onMounted } from "vue";
import { useAi } from "@/composables/useAi";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { polishDescription } from "@/composables/useTickets";

const props = defineProps({
  text: { type: String, default: "" },
});
const emit = defineEmits(["apply"]);

const { t } = useI18n();
const toast = useToast();
const { enabled, ensure } = useAi();
const busy = ref(false);
const preview = ref("");

const hasText = computed(() => !!(props.text || "").trim());

onMounted(ensure);

async function polish() {
  if (busy.value || !hasText.value) return;
  busy.value = true;
  try {
    const res = await polishDescription(props.text.trim());
    preview.value = res.polished || "";
  } catch (e) {
    toast.error(e.message || t("AI rewrite failed"));
  } finally {
    busy.value = false;
  }
}

function apply() {
  if (preview.value) emit("apply", preview.value);
  preview.value = "";
}
</script>
