<template>
  <div class="chart-frame">
    <svg viewBox="0 0 760 330" role="img" aria-label="会员 RFM 散点图">
      <g v-for="tick in yTicks" :key="tick.value">
        <line x1="58" :y1="tick.y" x2="744" :y2="tick.y" stroke="var(--line)" stroke-width="1" />
        <text x="52" :y="tick.y + 3" text-anchor="end" class="axis-label">{{ tick.label }}</text>
      </g>
      <g v-for="tick in xTicks" :key="tick.value">
        <line :x1="tick.x" y1="24" :x2="tick.x" y2="278" stroke="var(--line)" stroke-width="1" />
        <text :x="tick.x" y="296" text-anchor="middle" class="axis-label">{{ tick.label }}</text>
      </g>

      <circle
        v-for="point in rendered"
        :key="point.member_no"
        :cx="point.cx"
        :cy="point.cy"
        r="2.6"
        :fill="point.color"
        opacity="0.72"
      >
        <title>{{ point.member_no }} · 距今 {{ point.x }} 天 · {{ formatMoney(point.y) }}</title>
      </circle>

      <text x="58" y="316" class="axis-label">X · 距今天数（右=更久未到店）</text>
      <text x="744" y="316" text-anchor="end" class="axis-label">Y · 累计消费（对数刻度）</text>
    </svg>
    <div class="chart-legend">
      <span v-for="cluster in clusters" :key="cluster.cluster_key">
        <span class="swatch" :style="{ background: clusterColor(cluster.kind) }" />
        {{ cluster.cluster_key }} · {{ cluster.label }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { clusterColor } from '../../constants/clusterKinds'
import type { ClusterProfile, ScatterPoint } from '../../types/segment'
import { formatMoney } from '../../utils/formatNumber'

const props = defineProps<{
  points: ScatterPoint[]
  clusters: ClusterProfile[]
}>()

const PAD_LEFT = 58
const PAD_RIGHT = 16
const PAD_TOP = 24
const PAD_BOTTOM = 52
const width = 760
const height = 330

const xMax = computed(() => {
  const max = Math.max(60, ...props.points.map((point) => point.x))
  return Math.ceil(max / 50) * 50
})

const yMax = computed(() => Math.max(2000, ...props.points.map((point) => point.y)))

function xScale(value: number): number {
  return PAD_LEFT + (value / xMax.value) * (width - PAD_LEFT - PAD_RIGHT)
}

function yScale(value: number): number {
  const maxLog = Math.log10(yMax.value + 1)
  const ratio = Math.log10(Math.max(1, value) + 1) / maxLog
  return height - PAD_BOTTOM - ratio * (height - PAD_TOP - PAD_BOTTOM)
}

const kindByKey = computed(() => {
  const map = new Map<string, string>()
  for (const cluster of props.clusters) map.set(cluster.cluster_key, cluster.kind)
  return map
})

const rendered = computed(() =>
  props.points.map((point) => ({
    ...point,
    cx: xScale(point.x),
    cy: yScale(point.y),
    color: clusterColor(kindByKey.value.get(point.cluster_key)),
  })),
)

const yTicks = computed(() => {
  const ticks = [0, 300, 1000, 3000, 9000].filter((value) => value <= yMax.value)
  if (!ticks.includes(0)) ticks.unshift(0)
  return ticks.map((value) => ({
    value,
    y: yScale(value),
    label: value === 0 ? '0' : value >= 1000 ? `${value / 1000}k` : String(value),
  }))
})

const xTicks = computed(() => {
  const step = xMax.value / 4
  return [0, 1, 2, 3, 4].map((index) => ({
    value: Math.round(index * step),
    x: xScale(index * step),
    label: String(Math.round(index * step)),
  }))
})
</script>
