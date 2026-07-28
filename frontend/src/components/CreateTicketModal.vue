<template>
  <transition name="fade">
    <div
      v-if="ui.state.createOpen"
      class="fixed inset-0 z-50 bg-ink-900/40 flex items-start justify-center p-4 sm:p-8 overflow-y-auto"
      @click.self="close"
    >
      <div class="card w-full max-w-xl p-6 mt-6">
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold text-ink-900">New Ticket</h2>
          <button class="btn-ghost !px-2" @click="close">✕</button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="label">Title *</label>
            <input
              ref="titleEl"
              v-model="form.title"
              class="input"
              placeholder="Short summary of the task or problem"
              @keydown.meta.enter="submit"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Type</label>
              <select v-model="form.ticket_type" class="input">
                <option v-for="t in TYPES" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <div>
              <label class="label">Priority</label>
              <select v-model="form.priority" class="input">
                <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Source Portal</label>
              <select v-model="form.source_portal" class="input">
                <option v-for="p in PORTALS" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div>
              <label class="label">Due Date</label>
              <input v-model="form.due_date" type="date" class="input" />
            </div>
          </div>

          <div>
            <label class="label">Assign To</label>
            <select v-model="form.assigned_to" class="input">
              <option value="">— Unassigned —</option>
              <option v-for="u in users" :key="u.name" :value="u.name">
                {{ u.full_name || u.name }}
              </option>
            </select>
          </div>

          <div>
            <label class="label">Description</label>
            <textarea
              v-model="form.description"
              rows="4"
              class="input resize-none"
              placeholder="Add context, steps, links…"
            />
          </div>

          <div>
            <label class="label">Attachments</label>
            <input
              ref="fileEl"
              type="file"
              multiple
              accept="image/*,.pdf,.csv,.xlsx,.xls,.docx,.doc,.txt,.zip,.mp4,.mov,.webm"
              class="hidden"
              @change="onPickFiles"
            />
            <div class="flex flex-wrap items-center gap-2">
              <button class="btn-outline" type="button" @click="fileEl?.click()">
                📎 Add files
              </button>
              <span
                v-for="(f, i) in files"
                :key="i"
                class="inline-flex items-center gap-1.5 bg-ink-50 border border-ink-200 rounded-lg px-2.5 py-1 text-xs text-ink-700"
              >
                {{ f.name }}
                <button class="text-ink-400 hover:text-rose-600" type="button" @click="files.splice(i, 1)">✕</button>
              </span>
            </div>
          </div>

          <div v-if="form.linked_label" class="text-xs text-ink-500 bg-ink-50 rounded-lg px-3 py-2">
            🔗 Linked to <b>{{ form.linked_label }}</b>
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button class="btn-outline" @click="close">Cancel</button>
          <button class="btn-primary" :disabled="saving || !form.title.trim()" @click="submit">
            {{ saving ? "Creating…" : "Create Ticket" }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { reactive, ref, watch, nextTick } from "vue";
import { useUi } from "@/composables/useUi";
import { useToast } from "@/composables/useToast";
import {
  TYPES, PRIORITIES, PORTALS, createTicket, assignableUsers, uploadAttachment,
} from "@/composables/useTickets";

const ui = useUi();
const toast = useToast();
const saving = ref(false);
const users = ref([]);
const titleEl = ref(null);
const fileEl = ref(null);
const files = ref([]);

function onPickFiles(e) {
  files.value.push(...Array.from(e.target.files || []));
  e.target.value = "";
}

const blank = () => ({
  title: "",
  ticket_type: "Task",
  priority: "Medium",
  source_portal: "Other",
  assigned_to: "",
  due_date: "",
  description: "",
  linked_doctype: "",
  linked_name: "",
  linked_label: "",
  linked_url: "",
});

const form = reactive(blank());

watch(
  () => ui.state.createOpen,
  async (open) => {
    if (open) {
      Object.assign(form, blank(), ui.state.createPreset || {});
      files.value = [];
      if (!users.value.length) {
        try {
          users.value = await assignableUsers("");
        } catch {}
      }
      await nextTick();
      titleEl.value?.focus();
    }
  }
);

function close() {
  ui.closeCreate();
}

async function submit() {
  if (!form.title.trim() || saving.value) return;
  saving.value = true;
  try {
    const res = await createTicket({ ...form });
    let failed = 0;
    for (const f of files.value) {
      try {
        await uploadAttachment(res.name, f);
      } catch {
        failed++;
      }
    }
    files.value = [];
    if (failed) toast.error(`Ticket ${res.name} created, but ${failed} file(s) failed to upload`);
    else toast.success(`Ticket ${res.name} created`);
    ui.bump();
    close();
  } catch (e) {
    toast.error(e.message || "Could not create ticket");
  } finally {
    saving.value = false;
  }
}
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
