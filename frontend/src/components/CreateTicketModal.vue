<template>
  <transition name="fade">
    <div
      v-if="ui.state.createOpen"
      class="fixed inset-0 z-50 bg-ink-900/40 flex items-start justify-center p-0 sm:p-8 overflow-y-auto"
      @click.self="close"
    >
      <div class="card w-full max-w-xl p-5 sm:p-6 mt-0 sm:mt-6 rounded-none sm:rounded-2xl min-h-screen sm:min-h-0">
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

          <div class="grid grid-cols-2 gap-3" v-if="workspaces.length > 1 || templates.length">
            <div v-if="workspaces.length > 1">
              <label class="label">{{ t("Workspace") }}</label>
              <select v-model="form.workspace" class="input" @change="onWorkspaceChange">
                <option v-for="w in workspaces" :key="w.name" :value="w.name">
                  {{ w.icon }} {{ w.name }}
                </option>
              </select>
            </div>
            <div v-if="templates.length">
              <label class="label">{{ t("Template") }}</label>
              <select v-model="templateName" class="input" @change="applyTemplate">
                <option value="">{{ t("No template") }}</option>
                <option v-for="tp in templates" :key="tp.name" :value="tp.name">
                  {{ tp.template_name }}{{ tp.checklist.length ? ` (☑${tp.checklist.length})` : "" }}
                </option>
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
            <UserPicker v-model="form.assigned_to" :users="users" />
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
import UserPicker from "@/components/UserPicker.vue";
import { useWorkspaces } from "@/composables/useWorkspaces";
import { useI18n } from "@/composables/useI18n";
import { useUi } from "@/composables/useUi";
import { useToast } from "@/composables/useToast";
import {
  TYPES, PRIORITIES, PORTALS, createTicket, assignableUsers, uploadAttachment,
  listTemplates, createFromTemplate,
} from "@/composables/useTickets";

const ui = useUi();
const toast = useToast();
const { t } = useI18n();
const { workspaces, current: currentWsName } = useWorkspaces();
const saving = ref(false);
const users = ref([]);
const titleEl = ref(null);
const fileEl = ref(null);
const files = ref([]);
const templates = ref([]);
const templateName = ref("");

async function loadTemplates() {
  try {
    templates.value = form.workspace ? await listTemplates(form.workspace) : [];
  } catch {
    templates.value = [];
  }
  if (!templates.value.find((tp) => tp.name === templateName.value)) templateName.value = "";
}

function onWorkspaceChange() {
  templateName.value = "";
  loadTemplates();
}

function applyTemplate() {
  const tp = templates.value.find((x) => x.name === templateName.value);
  if (!tp) return;
  form.title = tp.title || tp.template_name;
  form.description = tp.description || "";
  form.ticket_type = tp.ticket_type || form.ticket_type;
  form.priority = tp.priority || form.priority;
  if (tp.default_assignee) form.assigned_to = tp.default_assignee;
}

function onPickFiles(e) {
  files.value.push(...Array.from(e.target.files || []));
  e.target.value = "";
}

const blank = () => ({
  title: "",
  workspace: "",
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
      // Default to the active workspace (or the system default).
      if (!form.workspace) {
        form.workspace =
          currentWsName.value ||
          (workspaces.value.find((w) => w.is_default) || workspaces.value[0] || {}).name ||
          "";
      }
      if (!users.value.length) {
        try {
          users.value = await assignableUsers("");
        } catch {}
      }
      loadTemplates();
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
    // A picked template creates via the template API so its checklist rides along.
    const res = templateName.value
      ? await createFromTemplate({
          template: templateName.value,
          title: form.title,
          description: form.description,
          due_date: form.due_date || "",
          assigned_to: form.assigned_to || "",
        })
      : await createTicket({ ...form });
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
