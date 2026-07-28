import { reactive } from "vue";

// Shared UI state for the global create-modal and ticket drawer, plus a
// monotonically-increasing `rev` other views watch to know data changed.
const state = reactive({
  createOpen: false,
  createPreset: {},
  drawerTicket: null, // ticket name currently open in the drawer
  rev: 0,
});

export function useUi() {
  return {
    state,
    openCreate(preset = {}) {
      state.createPreset = preset;
      state.createOpen = true;
    },
    closeCreate() {
      state.createOpen = false;
      state.createPreset = {};
    },
    openTicket(name) {
      state.drawerTicket = name;
    },
    closeTicket() {
      state.drawerTicket = null;
    },
    bump() {
      state.rev++;
    },
  };
}
