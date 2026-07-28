import { reactive } from "vue";

// Tiny global toast store shared across the app.
const state = reactive({ items: [] });
let seq = 0;

export function useToast() {
  function push(message, tone = "info", ttl = 3500) {
    const id = ++seq;
    state.items.push({ id, message, tone });
    setTimeout(() => dismiss(id), ttl);
    return id;
  }
  function dismiss(id) {
    const i = state.items.findIndex((t) => t.id === id);
    if (i !== -1) state.items.splice(i, 1);
  }
  return {
    items: state.items,
    dismiss,
    success: (m) => push(m, "success"),
    error: (m) => push(m, "error", 5000),
    info: (m) => push(m, "info"),
  };
}
