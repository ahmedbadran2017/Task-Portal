<template>
  <div class="relative">
    <!-- legend -->
    <div class="flex items-center gap-4 mb-3">
      <span v-for="s in SERIES" :key="s.key" class="inline-flex items-center gap-1.5 text-xs text-ink-600">
        <span class="w-2.5 h-2.5 rounded-[3px]" :style="{ background: s.color }" />
        {{ s.label }}
      </span>
    </div>

    <svg
      v-if="series.length"
      :viewBox="`0 0 ${W} ${H}`"
      class="w-full select-none"
      @mouseleave="hover = null"
    >
      <!-- recessive gridlines -->
      <g v-for="gy in gridY" :key="gy">
        <line :x1="PAD.l" :x2="W - PAD.r" :y1="y(gy)" :y2="y(gy)" stroke="#e7e5e4" stroke-width="1" />
        <text :x="PAD.l - 6" :y="y(gy) + 3" text-anchor="end" font-size="9" fill="#a8a29e">{{ gy }}</text>
      </g>
      <!-- baseline -->
      <line :x1="PAD.l" :x2="W - PAD.r" :y1="y(0)" :y2="y(0)" stroke="#d6d3d1" stroke-width="1" />

      <!-- bars -->
      <g v-for="(w, i) in series" :key="w.week">
        <rect
          v-for="(s, si) in SERIES"
          :key="s.key"
          :x="barX(i, si)"
          :y="y(w[s.key])"
          :width="barW"
          :height="Math.max(0, y(0) - y(w[s.key]))"
          :fill="s.color"
          rx="3"
          :opacity="hover === null || hover === i ? 1 : 0.35"
          style="transition: opacity 0.12s ease"
        />
        <!-- invisible hover hit target spanning the group -->
        <rect
          :x="groupX(i)" :y="PAD.t" :width="groupW" :height="H - PAD.t - PAD.b"
          fill="transparent"
          @mouseenter="hover = i"
        />
        <text
          :x="groupX(i) + groupW / 2"
          :y="H - 6"
          text-anchor="middle"
          font-size="9"
          fill="#78716c"
        >{{ weekLabel(w) }}</text>
      </g>
    </svg>

    <div v-else class="text-center py-8">
      <div class="text-3xl mb-2">📈</div>
      <p class="text-sm text-ink-400">Not enough history yet — trends appear after the first week.</p>
    </div>

    <!-- tooltip -->
    <div
      v-if="hover !== null && series[hover]"
      class="absolute top-1 right-1 card px-3 py-2 text-xs shadow-md"
    >
      <div class="font-semibold text-ink-800 mb-1">Week of {{ series[hover].start || series[hover].week }}</div>
      <div v-for="s in SERIES" :key="s.key" class="flex items-center gap-1.5 text-ink-600">
        <span class="w-2 h-2 rounded-[2px]" :style="{ background: s.color }" />
        {{ s.label }}: <b class="text-ink-900">{{ series[hover][s.key] }}</b>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({ series: { type: Array, default: () => [] } });

// Palette validated (dataviz six checks, light surface #fafaf9):
// rust #d45d3e ↔ blue #3b82f6 — CVD ΔE 27.2, normal 32.0, contrast ≥3:1.
const SERIES = [
  { key: "created", label: "Created", color: "#d45d3e" },
  { key: "resolved", label: "Resolved", color: "#3b82f6" },
];

const W = 640, H = 180;
const PAD = { l: 30, r: 8, t: 8, b: 20 };
const hover = ref(null);

const maxVal = computed(() =>
  Math.max(1, ...props.series.flatMap((w) => [w.created, w.resolved]))
);
const gridY = computed(() => {
  const m = maxVal.value;
  const step = m <= 4 ? 1 : Math.ceil(m / 4);
  const ticks = [];
  for (let v = step; v <= m; v += step) ticks.push(v);
  return ticks;
});

function y(v) {
  const usable = H - PAD.t - PAD.b;
  return PAD.t + usable - (v / maxVal.value) * usable;
}
const groupW = computed(() =>
  (W - PAD.l - PAD.r) / Math.max(1, props.series.length)
);
function groupX(i) {
  return PAD.l + i * groupW.value;
}
// two thin bars centred in the group, 2px surface gap between them
const barW = computed(() => Math.min(14, Math.max(4, groupW.value / 2 - 6)));
function barX(i, si) {
  const centre = groupX(i) + groupW.value / 2;
  return si === 0 ? centre - barW.value - 1 : centre + 1;
}
function weekLabel(w) {
  if (!w.start) return "";
  const d = new Date(w.start);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}
</script>
