<template>
  <div class="chart-frame">
    <svg viewBox="0 0 760 252" role="img" aria-label="RFM 五分位分数分布直方图">
      <g v-for="line in gridLines" :key="line.value">
        <line x1="46" :y1="line.y" x2="746" :y2="line.y" stroke="var(--line)" stroke-width="1" />
        <text x="40" :y="line.y + 3" text-anchor="end" class="axis-label">{{ line.label }}</text>
      </g>

      <g v-for="(group, groupIndex) in groups" :key="group.key">
        <text :x="50 + groupIndex * 236" y="16" class="group-label">{{ group.label }}</text>
        <g v-for="(count, index) in group.counts" :key="index">
          <rect
            :x="50 + groupIndex * 236 + index * 40"
            :y="200 - barHeight(count)"
            width="27"
            :height="barHeight(count)"
            :fill="group.color"
            opacity="0.9"
          />
          <text
            :x="63 + groupIndex * 236 + index * 40"
            :y="194 - barHeight(count)"
            text-anchor="middle"
            class="bar-value"
          >
            {{ count }}
          </text>
          <text
            :x="63 + groupIndex * 236 + index * 40"
            y="218"
            text-anchor="middle"
            class="axis-label"
          >
            {{ index + 1 }}
          </text>
        </g>
        <line
          :x1="50 + groupIndex * 236"
          y1="200"
          :x2="50 + groupIndex * 236 + 200"
          y2="200"
          stroke="var(--line-strong)"
        />
      </g>
      <text x="46" y="240" class="axis-label">五分位档位（1 最低 · 5 最高）· R 已反向</text>
    </svg>
    <div class="chart-legend">
      <span v-for="group in groups" :key="group.key">
        <span class="swatch" :style="{ background: group.color }" />{{ group.label }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Histograms } from '../../types/segment'

const props = defineProps<{ histograms: Histograms }>()

const dims = [
  { key: 'recency', label: 'R · 最近消费（已反向）', color: 'var(--rust)' },
  { key: 'frequency', label: 'F · 消费频次', color: 'var(--ochre)' },
  { key: 'monetary', label: 'M · 累计金额', color: 'var(--moss)' },
] as const

const groups = computed(() =>
  dims.map((dim) => ({
    ...dim,
    counts: props.histograms.score_distribution?.[dim.key] ?? [0, 0, 0, 0, 0],
  })),
)

const maxCount = computed(() => {
  const values = groups.value.flatMap((group) => group.counts)
  return Math.max(10, ...values)
})

function barHeight(count: number): number {
  return Math.round((count / maxCount.value) * 148)
}

const gridLines = computed(() =>
  [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    value: ratio,
    y: 200 - ratio * 148,
    label: String(Math.round(maxCount.value * ratio)),
  })),
)
</script>

<style scoped>
.group-label {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.1em;
  fill: var(--ink-2);
}
.bar-value {
  font-family: var(--font-body);
  font-size: 9.5px;
  fill: var(--ink-2);
  font-variant-numeric: tabular-nums;
}
</style>
