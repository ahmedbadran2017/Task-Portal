<template>
  <transition name="tmodal">
    <div
      v-if="ui.state.drawerTicket"
      class="fixed inset-0 z-50 bg-ink-900/50 overflow-y-auto"
      @click.self="close"
    >
      <div class="min-h-full flex items-start justify-center p-4 sm:p-8" @click.self="close">
        <div class="tmodal-panel w-full max-w-3xl bg-white rounded-2xl shadow-2xl my-4">
          <!-- header -->
          <div class="px-6 pt-5 pb-4 border-b border-ink-100 flex items-start justify-between gap-3">
            <div v-if="data" class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[11px] font-mono text-ink-400">{{ data.ticket.name }}</span>
                <Pill
                  :label="data.ticket.source_portal"
                  :color="portalMeta.color"
                  bg="#fafaf9"
                  dot
                />
                <Pill
                  v-if="data.ticket.sla_breached"
                  label="SLA breached"
                  color="#e11d48"
                  bg="#fff1f2"
                />
              </div>
              <h2 class="text-lg font-bold text-ink-900 mt-1.5 leading-snug">
                {{ data.ticket.title }}
              </h2>
            </div>
            <div v-else class="text-sm text-ink-400 py-2">Loading…</div>
            <button class="btn-ghost !px-2 shrink-0" @click="close">✕</button>
          </div>

          <!-- body: Trello-style two columns -->
          <div v-if="data" class="grid grid-cols-1 md:grid-cols-[1fr,240px]">
            <!-- ═══ main column ═══ -->
            <div class="px-6 py-5 space-y-6 min-w-0">
              <div v-if="data.ticket.description">
                <label class="label">Description</label>
                <div class="text-sm text-ink-700 prose-sm max-w-none" v-html="data.ticket.description" />
              </div>

              <!-- attachments -->
              <div>
                <div class="flex items-center justify-between mb-2">
                  <label class="label !mb-0">Attachments</label>
                  <input ref="fileEl" type="file" multiple class="hidden" @change="onUpload" />
                  <button class="btn-outline !px-2.5 !py-1 text-xs" :disabled="busy" @click="fileEl?.click()">
                    📎 Add
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
                      title="Remove"
                      @click.stop="onDeleteAttachment(a)"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <p v-else class="text-xs text-ink-400">No attachments.</p>
              </div>

              <!-- comments -->
              <div>
                <label class="label">Comments</label>
                <div class="space-y-2.5">
                  <div
                    v-for="(c, i) in data.comments"
                    :key="i"
                    class="flex gap-2.5"
                  >
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
                  <p v-if="!data.comments.length" class="text-xs text-ink-400">No comments yet.</p>
                </div>
                <div class="flex gap-2 mt-3">
                  <input
                    v-model="comment"
                    class="input"
                    placeholder="Write a comment… (@name mentions someone)"
                    @keydown.enter="postComment"
                  />
                  <button class="btn-primary" :disabled="busy || !comment.trim()" @click="postComment">
                    Send
                  </button>
                </div>
              </div>

              <!-- activity -->
              <div>
                <label class="label">Activity</label>
                <ul class="space-y-2 border-l-2 border-ink-100 pl-3">
                  <li v-for="(a, i) in data.activity" :key="i" class="text-xs text-ink-500">
                    <span class="font-medium text-ink-700">{{ a.action }}</span>
                    <span v-if="a.detail"> — {{ a.detail }}</span>
                    <span class="text-ink-400">
                      · {{ shortUser(a.actor) }} · {{ relTime(a.activity_on) }}</span
                    >
                  </li>
                </ul>
              </div>
            </div>

            <!-- ═══ sidebar (Trello-style controls) ═══ -->
            <div class="px-5 py-5 md:border-l border-t md:border-t-0 border-ink-100 bg-ink-50/60 rounded-b-2xl md:rounded-bl-none md:rounded-r-2xl space-y-4">
              <div>
                <label class="label">Status</label>
                <select
                  :value="data.ticket.status"
                  class="input"
                  :disabled="busy"
                  @change="onStatus($event.target.value)"
                >
                  <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
                </select>
              </div>
              <div>
                <label class="label">Priority</label>
                <select
                  :value="data.ticket.priority"
                  class="input"
                  :disabled="busy"
                  @change="onPriority($event.target.value)"
                >
                  <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
                </select>
              </div>
              <div>
                <label class="label">Assigned To</label>
                <select
                  :value="data.ticket.assigned_to || ''"
                  class="input"
                  :disabled="busy"
                  @change="onAssign($event.target.value)"
                >
                  <option value="">— Unassigned —</option>
                  <option v-for="u in users" :key="u.name" :value="u.name">
                    {{ u.full_name || u.name }}
                  </option>
                </select>
              </div>

              <div v-if="data.ticket.linked_label" class="pt-1">
                <label class="label">Linked Record</label>
                <a
                  v-if="data.ticket.linked_url"
                  :href="data.ticket.linked_url"
                  target="_blank"
                  rel="noopener"
                  class="text-sm text-brand-600 hover:underline break-all"
                  >🔗 {{ data.ticket.linked_label }}</a
                >
                <span v-else class="text-sm text-ink-700">🔗 {{ data.ticket.linked_label }}</span>
              </div>

              <div class="pt-2 border-t border-ink-200/60 space-y-2.5 text-sm">
                <Meta label="Type" :value="data.ticket.ticket_type" />
                <Meta label="Department" :value="data.ticket.department" />
                <Meta label="Reported by" :value="shortUser(data.ticket.reported_by)" />
                <Meta label="Created" :value="fmtDate(data.ticket.creation)" />
                <Meta label="SLA deadline" :value="fmtDate(data.ticket.sla_deadline)" />
                <Meta v-if="data.ticket.resolved_on" label="Resolved" :value="fmtDate(data.ticket.resolved_on)" />
                <Meta v-if="data.ticket.due_date" label="Due" :value="fmtDate(data.ticket.due_date)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch, h } from "vue";
import Pill from "./Pill.vue";
import { useUi } from "@/composables/useUi";
import { useToast } from "@/composables/useToast";
import {
  STATUSES, PRIORITIES, PORTAL_META, getTicket, updateStatus, setPriority,
  assignTicket, addComment, assignableUsers,
  uploadAttachment, deleteAttachment, isImage, fmtSize,
} from "@/composables/useTickets";
import { fmtDate, relTime } from "@/composables/useApi";

const Meta = (props) =>
  h("div", [
    h("div", { class: "text-[11px] text-ink-400 uppercase tracking-wide" }, props.label),
    h("div", { class: "text-ink-800" }, props.value || "—"),
  ]);
Meta.props = ["label", "value"];

const ui = useUi();
const toast = useToast();
const data = ref(null);
const users = ref([]);
const comment = ref("");
const busy = ref(false);
const fileEl = ref(null);

const portalMeta = computed(
  () => PORTAL_META[data.value?.ticket?.source_portal] || PORTAL_META.Other
);

watch(
  () => ui.state.drawerTicket,
  async (name) => {
    data.value = null;
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

async function onStatus(status) {
  await run(() => updateStatus(data.value.ticket.name, status), "Status updated");
}
async function onPriority(priority) {
  await run(() => setPriority(data.value.ticket.name, priority), "Priority updated");
}
async function onAssign(user) {
  await run(() => assignTicket(data.value.ticket.name, user || null), "Assignment updated");
}
async function postComment() {
  if (!comment.value.trim()) return;
  await run(() => addComment(data.value.ticket.name, comment.value.trim()), "Comment added");
  comment.value = "";
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
