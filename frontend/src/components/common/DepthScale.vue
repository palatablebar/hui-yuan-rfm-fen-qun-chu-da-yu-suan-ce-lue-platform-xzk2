<template>
  <div class="depth-scale" :class="{ horizontal }">
    <svg :viewBox="`0 0 ${horizontal ? 240 : 34} ${horizontal ? 26 : 220}`" role="img" aria-label="深度刻度">
      <line
        :x1="horizontal ? 4 : 26"
        :y1="horizontal ? 13 : 4"
        :x2="horizontal ? 232 : 26"
        :y2="horizontal ? 13 : 212"
        stroke="var(--line-strong)"
        stroke-width="1"
      />
      <g v-for="tick in ticks" :key="tick.value">
        <line
          :x1="horizontal ? 4 + (tick.value / max) * 228 : 20"
          :y1="horizontal ? 13 : 212 - (tick.value / max) * 208"
          :x2="horizontal ? 4 + (tick.value / max) * 228 : 26"
          :y2="horizontal ? 13 : 212 - (tick.value / max) * 208"
          stroke="var(--ink-3)"
          stroke-width="1"
        />
        <text
          :x="horizontal ? 4 + (tick.value / max) * 228 : 13"
          :y="horizontal ? 9 : 212 - (tick.value / max) * 208 + 3"
          :text-anchor="horizontal ? 'middle' : 'end'"
          class="tick"
        >
          {{ tick.label }}
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    max?: number
    labels?: number[]
    horizontal?: boolean
  }>(),
  { max: 600, labels: () => [0, 200, 400, 600], horizontal: false },
)

const ticks = computed(() =>
  props.labels.map((value) => ({ value, label: value === 0 ? '0 m' : String(value) })),
)
</script>

<style scoped>
.depth-scale {
  display: flex;
  align-items: center;
  justify-content: center;
}

.depth-scale svg {
  width: 34px;
  height: 220px;
}

.depth-scale.horizontal svg {
  width: 100%;
  height: 26px;
}

.tick {
  font-family: var(--font-body);
  font-size: 7.5px;
  letter-spacing: 0.04em;
  fill: var(--ink-3);
}
</style>
