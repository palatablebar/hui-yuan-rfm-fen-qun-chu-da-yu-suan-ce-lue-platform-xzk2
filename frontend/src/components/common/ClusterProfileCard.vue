<template>
  <button
    type="button"
    class="layer"
    :class="{ 'is-active': active }"
    :style="{ '--layer-color': clusterColor(cluster.kind) }"
    :data-testid="`cluster-${cluster.cluster_key}`"
    @click="$emit('select', cluster.cluster_key)"
  >
    <span class="layer-name">
      <strong>{{ cluster.cluster_key }} · {{ cluster.label }}</strong>
      <span class="kind">{{ cluster.kind.replaceAll('_', ' ') }}</span>
    </span>
    <span class="layer-metrics">
      <span><b>{{ cluster.member_count }}</b> 人</span>
      <span>可触达 <b>{{ cluster.reachable_count }}</b></span>
      <span>GMV 占比 <b>{{ formatPercent(cluster.gmv_share) }}</b></span>
      <span>核销率 <b>{{ formatPercent(cluster.redemption_rate) }}</b></span>
      <span class="score-hint">R/F/M {{ cluster.score_means.r.toFixed(1) }} / {{ cluster.score_means.f.toFixed(1) }} / {{ cluster.score_means.m.toFixed(1) }}</span>
    </span>
    <span class="layer-depth">{{ formatMoney(cluster.gmv_total) }}</span>
  </button>
  <p v-if="showAdvice" class="layer-advice">{{ cluster.advice }}</p>
</template>

<script setup lang="ts">
import { formatMoney, formatPercent } from '../../utils/formatNumber'
import { clusterColor } from '../../constants/clusterKinds'
import type { ClusterProfile } from '../../types/segment'

withDefaults(
  defineProps<{
    cluster: ClusterProfile
    active?: boolean
    showAdvice?: boolean
  }>(),
  { active: false, showAdvice: false },
)

defineEmits<{ select: [clusterKey: string] }>()
</script>

<style scoped>
.layer-advice {
  margin: 0 0 8px 20px;
  padding: 8px 12px;
  border-left: 2px solid color-mix(in oklch, var(--rust) 55%, transparent);
  font-size: var(--step--1);
  color: var(--ink-2);
  background: color-mix(in oklch, var(--sand-1) 30%, transparent);
}

.score-hint {
  letter-spacing: 0.04em;
  color: var(--ink-3);
}
</style>
