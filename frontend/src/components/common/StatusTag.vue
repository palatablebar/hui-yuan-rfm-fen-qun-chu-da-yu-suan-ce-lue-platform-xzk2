<template>
  <span class="tag" :data-tone="meta.tone">
    <span class="tag-dot" />
    {{ meta.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SEGMENT_STATUS_META } from '../../constants/segmentStatus'
import { STRATEGY_STATUS_META } from '../../constants/strategyStatus'
import type { SegmentStatus } from '../../types/segment'
import type { StrategyStatus } from '../../types/strategy'

const props = defineProps<{
  kind: 'segment' | 'strategy'
  value: SegmentStatus | StrategyStatus
}>()

const meta = computed(() => {
  if (props.kind === 'segment') {
    return SEGMENT_STATUS_META[props.value as SegmentStatus] ?? { label: String(props.value), tone: 'muted' }
  }
  return STRATEGY_STATUS_META[props.value as StrategyStatus] ?? { label: String(props.value), tone: 'muted' }
})
</script>

<style scoped>
.tag[data-tone='ok'] {
  color: var(--ok);
  border-color: color-mix(in oklch, var(--ok) 40%, var(--line-strong));
}
.tag[data-tone='danger'] {
  color: var(--danger);
  border-color: color-mix(in oklch, var(--danger) 40%, var(--line-strong));
}
.tag[data-tone='ochre'] {
  color: var(--ochre);
  border-color: color-mix(in oklch, var(--ochre) 46%, var(--line-strong));
}
</style>
