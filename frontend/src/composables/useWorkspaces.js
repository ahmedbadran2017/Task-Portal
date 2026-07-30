// Workspace context shared across the app: the list, the active workspace
// ("" = All), and its stages. Active choice persists per device.
import { ref, computed } from "vue";
import { callMethod, getMethod } from "./useApi";

const M = "task_hub.api.workspaces";

const workspaces = ref([]);
const current = ref(localStorage.getItem("th_ws") ?? "");
const loaded = ref(false);
let inflight = null;

async function load() {
  if (inflight) return inflight;
  inflight = _load().finally(() => (inflight = null));
  return inflight;
}

async function _load() {
  try {
    workspaces.value = await getMethod(`${M}.list_workspaces`);
    loaded.value = true;
    // First visit: land members in their own workspace, others in default.
    if (localStorage.getItem("th_ws") === null && workspaces.value.length) {
      const mine = workspaces.value.find((w) => w.is_member && !w.is_default);
      setCurrent(mine ? mine.name : "");
    }
    // Stale saved value (workspace deleted) → All.
    if (current.value && !workspaces.value.find((w) => w.name === current.value)) {
      setCurrent("");
    }
  } catch {
    /* not installed yet — switcher stays hidden */
  }
}

function setCurrent(name) {
  current.value = name;
  localStorage.setItem("th_ws", name);
}

const currentWs = computed(
  () => workspaces.value.find((w) => w.name === current.value) || null
);

export function useWorkspaces() {
  if (!loaded.value && !workspaces.value.length) load();
  return {
    workspaces,
    current,
    currentWs,
    setCurrent,
    reload: load,
    saveWorkspace: (ws) =>
      callMethod(`${M}.save_workspace`, {
        ...ws,
        stages: ws.stages ? JSON.stringify(ws.stages) : undefined,
      }),
    deleteWorkspace: (name) => callMethod(`${M}.delete_workspace`, { name }),
    moveStage: (name, stage) => callMethod(`${M}.move_stage`, { name, stage }),
    setTicketWorkspace: (name, workspace) =>
      callMethod(`${M}.set_ticket_workspace`, { name, workspace }),
    listDepartments: () => getMethod(`${M}.list_departments`),
  };
}
