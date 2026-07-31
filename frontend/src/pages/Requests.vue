<template>
  <div class="max-w-4xl mx-auto space-y-5">
    <div>
      <h2 class="text-lg font-bold text-ink-900">{{ t("Request something") }}</h2>
      <p class="text-sm text-ink-400">{{ t("Pick a form — your request lands on the right team's board.") }}</p>
    </div>

    <div v-if="error" class="card p-4 text-sm text-rose-600 bg-rose-50 border-rose-200">{{ error }}</div>

    <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <button
        v-for="f in forms"
        :key="f.name"
        class="card card-hover p-5 text-left rtl:text-right fade-up"
        @click="openForm(f)"
      >
        <div class="text-2xl mb-2">{{ f.icon || "📝" }}</div>
        <div class="text-sm font-bold text-ink-900">{{ f.form_name }}</div>
        <div class="text-[11px] text-ink-400 mt-0.5">
          {{ f.workspace_icon }} {{ f.workspace }}
        </div>
        <p v-if="f.help_text" class="text-xs text-ink-500 mt-2 line-clamp-2">{{ f.help_text }}</p>
      </button>
      <div v-for="i in (loading && !forms.length ? 3 : 0)" :key="'sk' + i" class="skeleton h-32" />
    </div>

    <div v-if="!forms.length && !loading" class="card p-10 text-center">
      <NavIcon name="inbox" :size="28" class="inline-block mb-2 text-ink-300" />
      <p class="text-sm text-ink-400">{{ t("No request forms yet — a manager can add them in Settings.") }}</p>
    </div>

    <!-- fill modal -->
    <transition name="fade">
      <div
        v-if="active"
        class="fixed inset-0 z-50 bg-ink-900/40 flex items-start justify-center p-0 sm:p-8 overflow-y-auto"
        @click.self="active = null"
      >
        <div class="card w-full max-w-lg p-5 sm:p-6 mt-0 sm:mt-6 rounded-none sm:rounded-2xl min-h-screen sm:min-h-0">
          <div class="flex items-center justify-between mb-1">
            <h2 class="text-lg font-semibold text-ink-900">{{ active.icon }} {{ active.form_name }}</h2>
            <button class="btn-ghost !px-2" @click="active = null"><NavIcon name="x" :size="12" /></button>
          </div>
          <p class="text-xs text-ink-400 mb-4">
            {{ active.workspace_icon }} {{ active.workspace }}
            <template v-if="active.help_text"> — {{ active.help_text }}</template>
          </p>

          <div class="space-y-4">
            <div>
              <label class="label">{{ t("Title") }} *</label>
              <input ref="titleEl" v-model="fill.title" class="input" maxlength="150" />
            </div>

            <div v-for="(q, i) in active.questions" :key="i">
              <label class="label">{{ q.question }} <template v-if="q.required">*</template></label>
              <textarea
                v-if="q.fieldtype === 'Long Text'"
                v-model="fill.answers[i]"
                rows="3"
                class="input resize-y"
              />
              <select v-else-if="q.fieldtype === 'Select'" v-model="fill.answers[i]" class="input">
                <option value=""></option>
                <option v-for="o in q.options" :key="o" :value="o">{{ o }}</option>
              </select>
              <input v-else-if="q.fieldtype === 'Date'" v-model="fill.answers[i]" type="date" class="input" />
              <input v-else-if="q.fieldtype === 'Number'" v-model="fill.answers[i]" type="number" class="input" />
              <label v-else-if="q.fieldtype === 'Checkbox'" class="flex items-center gap-2 text-sm text-ink-700">
                <input
                  type="checkbox"
                  class="rounded"
                  :checked="fill.answers[i] === 'Yes'"
                  @change="fill.answers[i] = $event.target.checked ? 'Yes' : ''"
                />
                {{ t("Yes") }}
              </label>
              <input v-else v-model="fill.answers[i]" class="input" />
            </div>

            <div class="w-44">
              <label class="label">{{ t("Due Date") }}</label>
              <input v-model="fill.due_date" type="date" class="input" />
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-6">
            <button class="btn-outline" @click="active = null">{{ t("Cancel") }}</button>
            <button class="btn-primary" :disabled="busy || !canSubmit" @click="submit">
              {{ busy ? t("Sending…") : t("Send request") }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
// Work intake: form cards → dynamic questions → a ticket on the owning
// team's board. The request lives in the requester's "Reported by me" view
// and the team's workspace at the same time.
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from "vue";
import NavIcon from "@/components/NavIcon.vue";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { useUi } from "@/composables/useUi";
import { listForms, submitForm } from "@/composables/useTickets";

const { t } = useI18n();
const toast = useToast();
const ui = useUi();

const forms = ref([]);
const loading = ref(true);
const error = ref("");
const active = ref(null);
const busy = ref(false);
const titleEl = ref(null);
const fill = reactive({ title: "", answers: [], due_date: "" });

const canSubmit = computed(() => {
  if (!fill.title.trim()) return false;
  if (!active.value) return false;
  return active.value.questions.every(
    (q, i) => !q.required || String(fill.answers[i] || "").trim()
  );
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    forms.value = await listForms();
  } catch (e) {
    error.value = e.message || "Could not load forms";
  } finally {
    loading.value = false;
  }
}

async function openForm(f) {
  active.value = f;
  fill.title = "";
  fill.due_date = "";
  fill.answers = f.questions.map(() => "");
  await nextTick();
  titleEl.value?.focus();
}

async function submit() {
  if (!canSubmit.value || busy.value) return;
  busy.value = true;
  try {
    const answers = active.value.questions.map((q, i) => ({
      question: q.question,
      answer: String(fill.answers[i] || ""),
    }));
    const res = await submitForm(active.value.name, fill.title.trim(), answers, fill.due_date || "");
    toast.success(t("Request sent — {0}", res.name));
    active.value = null;
    ui.bump();
  } catch (e) {
    toast.error(e.message || "Could not send the request");
  } finally {
    busy.value = false;
  }
}

onMounted(load);

// Esc closes the overlay — keyboard users had no way out.
function onEscKey(e) {
  if (e.key === "Escape" && active.value) active.value = null;
}
onMounted(() => document.addEventListener("keydown", onEscKey));
onUnmounted(() => document.removeEventListener("keydown", onEscKey));
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>