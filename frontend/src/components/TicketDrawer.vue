<template>
  <transition name="tmodal">
    <div
      v-if="ui.state.drawerTicket"
      class="fixed inset-0 z-50 bg-ink-900/50 overflow-y-auto"
      @click.self="close"
    >
      <div class="min-h-full flex items-start justify-center p-0 sm:p-8" @click.self="close">
        <div class="tmodal-panel w-full max-w-3xl bg-white rounded-none sm:rounded-2xl shadow-2xl my-0 sm:my-4 min-h-screen sm:min-h-0">
          <!-- header -->
          <div class="px-6 pt-5 pb-4 border-b border-ink-100 flex items-start justify-between gap-3">
            <div v-if="data" class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[11px] font-mono text-ink-400">{{ data.ticket.name }}</span>
                <Pill :label="data.ticket.source_portal" :color="portalMeta.color" bg="#fafaf9" dot />
                <Pill v-if="data.ticket.sla_breached" :label="t('SLA breached')" color="#e11d48" bg="#fff1f2" />
              </div>
              <input
                v-if="editing"
                v-model="edit.title"
                class="input mt-1.5 !text-lg !font-bold"
                maxlength="180"
              />
              <h2 v-else class="text-lg font-bold text-ink-900 mt-1.5 leading-snug">
                {{ data.ticket.title }}
              </h2>
            </div>
            <div v-else class="text-sm text-ink-400 py-2">Loading…</div>
            <div class="flex items-center gap-1 shrink-0">
              <button
                v-if="data && !editing"
                class="btn-ghost !px-2.5 !py-1.5 text-xs"
                :class="data.watching ? '!text-brand-600 font-bold' : ''"
                @click="onWatch"
              >
                {{ data.watching ? "👁 " + t("Watching") : "👁 " + t("Watch") }}
              </button>
              <button
                v-if="data && canShowEdit && !editing"
                class="btn-ghost !px-2.5 !py-1.5 text-xs"
                @click="startEdit"
              >
                ✎ {{ t("Edit") }}
              </button>
              <button class="btn-ghost !px-2" @click="close">✕</button>
            </div>
          </div>

          <!-- body -->
          <div v-if="data" class="grid grid-cols-1 md:grid-cols-[1fr,240px]">
            <!-- main column -->
            <div class="px-6 py-5 space-y-6 min-w-0">
              <!-- edit mode -->
              <div v-if="editing" class="space-y-3">
                <div>
                  <label class="label">{{ t("Description") }}</label>
                  <textarea v-model="edit.description" rows="5" class="input resize-y" />
                  <AiPolish :text="edit.description" @apply="edit.description = $event" />
                </div>
                <div class="w-44">
                  <label class="label">{{ t("Due Date") }}</label>
                  <input v-model="edit.due_date" type="date" class="input" />
                </div>
                <div class="flex gap-2 justify-end">
                  <button class="btn-outline" @click="editing = false">{{ t("Cancel") }}</button>
                  <button class="btn-primary" :disabled="busy || !edit.title.trim()" @click="saveEdit">
                    {{ busy ? t("Saving…") : t("Save") }}
                  </button>
                </div>
              </div>

              <div v-else-if="data.ticket.description">
                <label class="label">{{ t("Description") }}</label>
                <div class="text-sm text-ink-700 prose-sm max-w-none" v-html="data.ticket.description" />
              </div>

              <!-- checklist -->
              <div>
                <div class="flex items-center justify-between mb-2">
                  <label class="label !mb-0">{{ t("Checklist") }}</label>
                  <span v-if="data.checklist?.length" class="text-[11px] font-semibold text-ink-400">
                    {{ doneCount }}/{{ data.checklist.length }}
                  </span>
                </div>
                <div v-if="data.checklist?.length" class="h-1.5 rounded-full bg-ink-100 overflow-hidden mb-2.5">
                  <div
                    class="h-full rounded-full bg-emerald-500 transition-all duration-300"
                    :style="{ width: (doneCount / data.checklist.length) * 100 + '%' }"
                  />
                </div>
                <div class="space-y-1.5">
                  <div
                    v-for="c in data.checklist"
                    :key="c.name"
                    class="group flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-ink-50"
                  >
                    <button
                      class="w-4.5 h-4.5 w-[18px] h-[18px] rounded border-2 grid place-items-center text-[10px] shrink-0 transition"
                      :class="c.done ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-ink-300 text-transparent'"
                      :disabled="busy"
                      @click="onChecklistToggle(c)"
                    >✓</button>
                    <span class="text-sm flex-1" :class="c.done ? 'text-ink-400 line-through' : 'text-ink-800'">
                      {{ c.item }}
                    </span>
                    <button
                      class="text-ink-300 hover:text-rose-600 text-xs opacity-0 group-hover:opacity-100 transition"
                      @click="onChecklistRemove(c)"
                    >✕</button>
                  </div>
                </div>
                <div class="flex gap-2 mt-2">
                  <input
                    v-model="newItem"
                    class="input !py-1.5 text-sm"
                    :placeholder="t('Add a checklist item…')"
                    @keydown.enter="onChecklistAdd"
                  />
                  <button class="btn-outline !py-1.5" :disabled="busy || !newItem.trim()" @click="onChecklistAdd">
                    +
                  </button>
                </div>
              </div>

              <!-- attachments -->
              <div>
                <div class="flex items-center justify-between mb-2">
                  <label class="label !mb-0">{{ t("Attachments") }}</label>
                  <input ref="fileEl" type="file" multiple class="hidden" @change="onUpload" />
                  <button class="btn-outline !px-2.5 !py-1 text-xs" :disabled="busy" @click="fileEl?.click()">
                    📎 {{ t("Add") }}
                  </button>
                </div>
                <div v-if="data.attachments?.length" class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  <div
                    v-for="a in data.attachments"
                    :key="a.name"
                    class="group relative border border-ink-200 rounded-xl overflow-hidden bg-ink-50"
                  >
                    <a :href="a.file_url" target="_blank" rel="noopener" class="block">
                      <img
                        v-if="isImage(a.file_url)"
                        :src="a.file_url"
                        :alt="a.file_name"
                        class="w-full h-24 object-cover"
                      />
                      <div v-else class="h-24 grid place-items-center text-2xl">📄</div>
                      <div class="px-2 py-1.5 bg-white border-t border-ink-100">
                        <div class="text-[11px] font-medium text-ink-700 truncate">{{ a.file_name }}</div>
                        <div class="text-[10px] text-ink-400">{{ fmtSize(a.file_size) }}</div>
                      </div>
                    </a>
                    <button
                      class="absolute top-1 right-1 w-6 h-6 rounded-full bg-ink-900/60 text-white text-xs opacity-0 group-hover:opacity-100 transition"
                      @click.stop="onDeleteAttachment(a)"
                    >✕</button>
                  </div>
                </div>
                <p v-else class="text-xs text-ink-400">{{ t("No attachments.") }}</p>
              </div>

              <!-- comments -->
              <div>
                <label class="label">{{ t("Comments") }}</label>
                <div class="space-y-2.5">
                  <div v-for="(c, i) in data.comments" :key="i" class="flex gap-2.5">
                    <span
                      class="w-7 h-7 rounded-full grid place-items-center text-[10px] font-bold text-white shrink-0 mt-0.5"
                      :style="{ background: avatarColor(c.author) }"
                    >{{ initials(c.author) }}</span>
                    <div class="flex-1 bg-ink-50 rounded-xl px-3 py-2">
                      <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold text-ink-700">{{ shortUser(c.author) }}</span>
                        <span class="text-[11px] text-ink-400">{{ relTime(c.comment_on) }}</span>
                      </div>
                      <p class="text-sm text-ink-800 mt-0.5 whitespace-pre-wrap">{{ c.message }}</p>
                    </div>
                  </div>
                  <p v-if="!data.comments.length" class="text-xs text-ink-400">{{ t("No comments yet.") }}</p>
                </div>
                <div class="relative mt-3">
                  <div
                    v-if="mentionMatches.length"
                    class="absolute bottom-full mb-1 left-0 w-64 bg-white border border-ink-200 rounded-xl shadow-lg z-20 overflow-hidden"
                  >
                    <button
                      v-for="u in mentionMatches"
                      :key="u.name"
                      class="w-full text-left px-3 py-2 text-sm hover:bg-brand-50/60 flex items-center gap-2"
                      @click="insertMention(u)"
                    >
                      <span class="font-semibold text-ink-800">{{ u.full_name || u.name }}</span>
                      <span class="text-[10px] text-ink-400 truncate">@{{ u.name.split("@")[0] }}</span>
                    </button>
                    <p class="px-3 py-1.5 text-[10px] text-ink-400 bg-ink-50">Tab ↹</p>
                  </div>
                  <div class="flex gap-2">
                    <input
                      v-model="comment"
                      class="input"
                      :placeholder="t('Write a comment… type @ to mention')"
                      @keydown.tab.prevent="mentionMatches.length && insertMention(mentionMatches[0])"
                      @keydown.enter="onCommentEnter"
                    />
                    <button class="btn-primary" :disabled="busy || !comment.trim()" @click="postComment">
                      {{ t("Send") }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- activity -->
              <div>
                <label class="label">{{ t("Activity") }}</label>
                <ul class="space-y-2 border-l-2 border-ink-100 pl-3">
                  <li v-for="(a, i) in data.activity" :key="i" class="text-xs text-ink-500">
                    <span class="font-medium text-ink-700">{{ a.action }}</span>
                    <span v-if="a.detail"> — {{ a.detail }}</span>
                    <span class="text-ink-400">
                      · {{ shortUser(a.actor) }} · {{ relTime(a.activity_on) }}</span>
                  </li>
                </ul>
              </div>
            </div>

            <!-- sidebar -->
            <div class="px-5 py-5 md:border-l border-t md:border-t-0 border-ink-100 bg-ink-50/60 rounded-b-2xl md:rounded-bl-none md:rounded-r-2xl space-y-4">
              <div v-if="ticketStages.length">
                <label class="label">{{ t("Stage") }}</label>
                <select :value="data.ticket.stage" class="input" :disabled="busy" @change="onStage($event.target.value)">
                  <option v-for="s in ticketStages" :key="s.stage_name" :value="s.stage_name">
                    {{ t(s.stage_name) }}
                  </option>
                </select>
              </div>
              <div v-else>
                <label class="label">{{ t("Status") }}</label>
                <select :value="data.ticket.status" class="input" :disabled="busy" @change="onStatus($event.target.value)">
                  <option v-for="s in STATUSES" :key="s" :value="s">{{ t(s) }}</option>
                </select>
              </div>
              <div v-if="workspaces.length > 1">
                <label class="label">{{ t("Workspace") }}</label>
                <select :value="data.ticket.workspace" class="input" :disabled="busy" @change="onWorkspace($event.target.value)">
                  <option v-for="w in workspaces" :key="w.name" :value="w.name">
                    {{ w.icon }} {{ w.name }}
                  </option>
                </select>
              </div>
              <div>
                <label class="label">{{ t("Priority") }}</label>
                <select :value="data.ticket.priority" class="input" :disabled="busy" @change="onPriority($event.target.value)">
                  <option v-for="p in PRIORITIES" :key="p" :value="p">{{ t(p) }}</option>
                </select>
              </div>
              <div>
                <label class="label">{{ t("Assigned To") }}</label>
                <UserPicker
                  :model-value="data.ticket.assigned_to || ''"
                  :users="users"
                  :disabled="busy"
                  @update:model-value="onAssign"
                />
              </div>

              <div v-if="data.ticket.linked_label" class="pt-1">
                <label class="label">{{ t("Linked Record") }}</label>
                <a
                  v-if="data.ticket.linked_url"
                  :href="data.ticket.linked_url"
                  target="_blank"
                  rel="noopener"
                  class="text-sm text-brand-600 hover:underline break-all"
                >🔗 {{ data.ticket.linked_label }}</a>
                <span v-else class="text-sm text-ink-700">🔗 {{ data.ticket.linked_label }}</span>
              </div>

              <div class="pt-2 border-t border-ink-200/60 space-y-2.5 text-sm">
                <Meta :label="t('Type')" :value="t(data.ticket.ticket_type)" />
                <Meta :label="t('Department')" :value="data.ticket.department" />
                <Meta :label="t('Reported by')" :value="shortUser(data.ticket.reported_by)" />
                <Meta :label="t('Created')" :value="fmtDate(data.ticket.creation)" />
                <Meta :label="t('SLA deadline')" :value="fmtDate(data.ticket.sla_deadline)" />
                <Meta v-if="data.ticket.resolved_on" :label="t('Resolved')" :value="fmtDate(data.ticket.resolved_on)" />
                <Meta v-if="data.ticket.due_date" :label="t('Due')" :value="fmtDate(data.ticket.due_date)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, reactive, computed, watch, h } from "vue";
import Pill from "./Pill.vue";
import UserPicker from "./UserPicker.vue";
import AiPolish from "./AiPolish.vue";
import { useUi } from "@/composables/useUi";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";
import { useWorkspaces } from "@/composables/useWorkspaces";
import {
  STATUSES, PRIORITIES, PORTAL_META, getTicket, updateStatus, setPriority,
  assignTicket, addComment, assignableUsers, updateTicket, watchTicket,
  checklistAdd, checklistToggle, checklistRemove,
  uploadAttachment, deleteAttachment, isImage, fmtSize,
} from "@/composables/useTickets";
import { fmtDate, relTime, currentUserId, hasRole } from "@/composables/useApi";

const Meta = (props) =>
  h("div", [
    h("div", { class: "text-[11px] text-ink-400 uppercase tracking-wide" }, props.label),
    h("div", { class: "text-ink-800" }, props.value || "—"),
  ]);
Meta.props = ["label", "value"];

const ui = useUi();
const toast = useToast();
const { t } = useI18n();
const { workspaces, moveStage, setTicketWorkspace } = useWorkspaces();
const data = ref(null);
const users = ref([]);
const comment = ref("");
const busy = ref(false);
const fileEl = ref(null);
const newItem = ref("");
const editing = ref(false);
const edit = reactive({ title: "", description: "", due_date: "" });

const doneCount = computed(
  () => (data.value?.checklist || []).filter((c) => c.done).length
);

const canShowEdit = computed(() => {
  const tk = data.value?.ticket;
  if (!tk) return false;
  const me = currentUserId();
  return (
    tk.reported_by === me || tk.assigned_to === me ||
    hasRole("Task Hub Admin", "Task Hub Manager")
  );
});

// Mention suggestions only when "@" starts a word (not inside an email).
const mentionMatches = computed(() => {
  const m = comment.value.match(/(^|\s)@([A-Za-z0-9._-]*)$/);
  if (!m) return [];
  const q = m[2].toLowerCase();
  return users.value
    .filter(
      (u) =>
        (u.full_name || "").toLowerCase().includes(q) ||
        u.name.toLowerCase().startsWith(q)
    )
    .slice(0, 5);
});

function insertMention(u) {
  comment.value = comment.value.replace(
    /@([A-Za-z0-9._-]*)$/,
    "@" + u.name.split("@")[0] + " "
  );
}

const ticketStages = computed(() => {
  const ws = workspaces.value.find((w) => w.name === data.value?.ticket?.workspace);
  return ws?.stages || [];
});

const portalMeta = computed(
  () => PORTAL_META[data.value?.ticket?.source_portal] || PORTAL_META.Other
);

watch(
  () => ui.state.drawerTicket,
  async (name) => {
    data.value = null;
    editing.value = false;
    if (!name) return;
    await load(name);
    if (!users.value.length) {
      try {
        users.value = await assignableUsers("");
      } catch {}
    }
  }
);

async function load(name) {
  try {
    data.value = await getTicket(name);
  } catch (e) {
    toast.error(e.message || "Could not load ticket");
    close();
  }
}

function close() {
  ui.closeTicket();
}

function startEdit() {
  const tk = data.value.ticket;
  edit.title = tk.title;
  edit.description = stripHtmlForEdit(tk.description || "");
  edit.due_date = tk.due_date || "";
  editing.value = true;
}

// The stored description may carry the editor's HTML — edit as plain text.
function stripHtmlForEdit(html) {
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.innerText || "";
}

async function saveEdit() {
  await run(
    () =>
      updateTicket(data.value.ticket.name, {
        title: edit.title,
        description: edit.description,
        due_date: edit.due_date || "",
      }),
    "Saved"
  );
  editing.value = false;
}

async function onWatch() {
  const watching = data.value.watching;
  await run(() => watchTicket(data.value.ticket.name, !watching), watching ? "Unwatched" : "Watching");
}

async function onChecklistAdd() {
  if (!newItem.value.trim()) return;
  const item = newItem.value.trim();
  newItem.value = "";
  await run(() => checklistAdd(data.value.ticket.name, item), "Added");
}
async function onChecklistToggle(c) {
  await run(() => checklistToggle(data.value.ticket.name, c.name), "Updated");
}
async function onChecklistRemove(c) {
  await run(() => checklistRemove(data.value.ticket.name, c.name), "Removed");
}

async function onStatus(status) {
  await run(() => updateStatus(data.value.ticket.name, status), "Status updated");
}
async function onStage(stage) {
  await run(() => moveStage(data.value.ticket.name, stage), "Stage updated");
}
async function onWorkspace(ws) {
  await run(() => setTicketWorkspace(data.value.ticket.name, ws), "Workspace updated");
}
async function onPriority(priority) {
  await run(() => setPriority(data.value.ticket.name, priority), "Priority updated");
}
async function onAssign(user) {
  await run(() => assignTicket(data.value.ticket.name, user || null), "Assignment updated");
}
function onCommentEnter() {
  // With suggestions open, Enter is reserved — Tab (or click) inserts the
  // mention; the Send button always works regardless.
  if (!mentionMatches.value.length) postComment();
}

async function postComment() {
  if (!comment.value.trim()) return;
  const msg = comment.value.trim();
  comment.value = "";
  await run(() => addComment(data.value.ticket.name, msg), "Comment added");
}

async function onUpload(e) {
  const picked = Array.from(e.target.files || []);
  e.target.value = "";
  if (!picked.length) return;
  busy.value = true;
  try {
    for (const f of picked) await uploadAttachment(data.value.ticket.name, f);
    await load(data.value.ticket.name);
    toast.success(picked.length > 1 ? `${picked.length} files attached` : "File attached");
  } catch (err) {
    toast.error(err.message || "Upload failed");
  } finally {
    busy.value = false;
  }
}

async function onDeleteAttachment(a) {
  await run(() => deleteAttachment(data.value.ticket.name, a.name), "Attachment removed");
}

async function run(fn, okMsg) {
  busy.value = true;
  try {
    await fn();
    await load(data.value.ticket.name);
    ui.bump();
    toast.success(okMsg);
  } catch (e) {
    toast.error(e.message || "Action failed");
  } finally {
    busy.value = false;
  }
}

function shortUser(u) {
  return u ? String(u).split("@")[0] : "—";
}
const AVATAR_COLORS = ["#d45d3e", "#7c3aed", "#059669", "#2563eb", "#d97706", "#0891b2", "#9f1239"];
function avatarColor(u) {
  let hash = 0;
  for (const ch of String(u || "")) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}
function initials(u) {
  return String(u || "?").split("@")[0].slice(0, 2).toUpperCase();
}
</script>

<style scoped>
.tmodal-enter-active,
.tmodal-leave-active {
  transition: opacity 0.18s ease;
}
.tmodal-enter-active .tmodal-panel,
.tmodal-leave-active .tmodal-panel {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.tmodal-enter-from,
.tmodal-leave-to {
  opacity: 0;
}
.tmodal-enter-from .tmodal-panel,
.tmodal-leave-to .tmodal-panel {
  transform: translateY(12px) scale(0.98);
  opacity: 0;
}
</style>
