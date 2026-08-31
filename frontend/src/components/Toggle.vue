<script>
// Extracted from Settings.vue so the phone-notification card can reuse the
// exact same switch rather than growing a second one that drifts.
import { h } from "vue";

export default {
  name: "AppToggle",
  props: { modelValue: [Number, Boolean], disabled: Boolean },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () =>
      h(
        "button",
        {
          type: "button",
          class: [
            "relative w-10 h-6 rounded-full transition-colors shrink-0",
            props.modelValue ? "bg-brand-500" : "bg-ink-200",
            props.disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
          ],
          onClick: () =>
            !props.disabled && emit("update:modelValue", props.modelValue ? 0 : 1),
        },
        [
          h("span", {
            class: [
              "absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all",
              // start/end respect the document direction; `left` never did.
              props.modelValue ? "start-[18px]" : "start-0.5",
            ],
          }),
        ]
      );
  },
};
</script>
