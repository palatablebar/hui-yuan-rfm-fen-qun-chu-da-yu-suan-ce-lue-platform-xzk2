<template>
  <div class="chart-frame">
    <svg viewBox="0 0 380 158" role="img" aria-label="轮廓系数随 k 的曲线">
      <g v-for="line in grid" :key="line.value">
        <line x1="34" :y1="line.y" x2="368" :y2="line.y" stroke="var(--line)" />
        <text x="28" :y="line.y + 3" text-anchor="end" class="axis-label">{{ line.label }}</text>
      </g>
      <polyline
        :points="linePoints"
        fill="none"
        stroke="var(--ink-2)"
        stroke-width="1.4"
      />
      <g v-for="point in coords" :key="point.k">
        <circle
          :cx="point.x"
          :cy="point.y"
          :r="point.k === selectedK ? 5 : 3"
          :fill="point.k === selectedK ? 'var(--rust)' : 'var(--paper)'"
          :stroke="point.k === selectedK ? 'var(--rust)' : 'var(--ink-2)'"
          stroke-width="1.3"
        />
        <text :x="point.x" y="146" text-anchor="middle" class="axis-label">k={{ point.k }}</text>
        <text
          v-if="point.k === selectedK"
          :x="point.x"
          :y="point.y - 10"
          text-anchor="middle"
          class="selected-label"
        >
          {{ point.silhouette.toFixed(3) }}
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SilhouettePoint } from '../../types/segment'

const props = defineProps<{
  curve: SilhouettePoint[]
  selectedK: number | null
}>()

const width = 380
const height = 158
const padLeft = 34
const padRight = 12
const padTop = 16
const padBottom = 24

const minValue = computed(() => Math.min(...props.curve.map((point) => point.silhouette), 0))
const maxValue = computed(() => Math.max(...props.curve.map((point) => point.silhouette), 0.1))

const coords = computed(() => {
  const list = props.curve
  if (!list.length) return []
  const span = Math.max(0.01, maxValue.value - minValue.value)
  return list.map((point, index) => ({
    ...point,
    x: padLeft + (index / Math.max(1, list.length - 1)) * (width - padLeft - padRight),
    y:
      height -
      padBottom -
      ((point.silhouette - minValue.value) / span) * (height - padTop - padBottom),
  }))
})

const linePoints = computed(() => coords.value.map((point) => `${point.x},${point.y}`).join(' '))

const grid = computed(() => {
  const span = maxValue.value - minValue.value
  return [0, 0.5, 1].map((ratio) => ({
    value: ratio,
    y: height - padBottom - ratio * (height - padTop - padBottom),
    label: (minValue.value + span * ratio).toFixed(2),
  }))
})
</script>

<style scoped>
.selected-label {
  font-family: var(--font-body);
  font-size: 9px;
  fill: var(--rust);
}
</style>
