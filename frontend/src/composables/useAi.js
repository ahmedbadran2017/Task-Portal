// AI-assist availability — one whoami round-trip per session, shared
// module-level so every description box doesn't re-ask.
import { ref } from "vue";
import { whoami } from "./useTickets";

const enabled = ref(false);
let checked = null;

export function useAi() {
  function ensure() {
    if (!checked) {
      checked = whoami()
        .then((me) => (enabled.value = !!me.ai_polish))
        .catch(() => (enabled.value = false));
    }
    return checked;
  }
  return { enabled, ensure };
}
