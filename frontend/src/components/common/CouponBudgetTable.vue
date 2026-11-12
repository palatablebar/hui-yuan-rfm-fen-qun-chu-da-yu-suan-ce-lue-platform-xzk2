<template>
  <div class="scroll-x">
    <table class="data-table" data-testid="budget-table">
      <thead>
        <tr>
          <th>簇</th>
          <th>券面额</th>
          <th class="num">预算</th>
          <th class="num">可触达</th>
          <th class="num">核销率</th>
          <th class="num">预计核销券</th>
          <th class="num">预计增量 GMV</th>
          <th class="num">ROI</th>
          <th>档位</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in allocations" :key="row.cluster_key">
          <td>
            <span class="cluster-cell">
              <span class="swatch" :style="{ background: clusterColor(row.kind) }" />
              {{ row.cluster_key }} · {{ row.label }}
            </span>
          </td>
          <td><b class="face">¥{{ row.coupon_face }}</b></td>
          <td class="num">{{ formatMoney(row.budget) }}</td>
          <td class="num">{{ row.reachable_count }}</td>
          <td class="num">{{ formatPercent(row.redemption_rate) }}</td>
          <td class="num">{{ row.expected_redemptions.toFixed(1) }}</td>
          <td class="num">{{ formatMoney(row.expected_gmv) }}</td>
          <td class="num">{{ formatRoi(row.roi) }}</td>
          <td><span class="tag">{{ row.tier_rank }} / {{ allocations.length }}</span></td>
        </tr>
      </tbody>
      <tfoot v-if="totals">
        <tr>
          <td colspan="2"><strong>合计</strong></td>
          <td class="num"><strong>{{ formatMoney(totals.budget) }}</strong></td>
          <td class="num">{{ totals.reachable_members }}</td>
          <td class="num">—</td>
          <td class="num"><strong>{{ totals.expected_redemptions.toFixed(1) }}</strong></td>
          <td class="num"><strong>{{ formatMoney(totals.expected_gmv) }}</strong></td>
          <td class="num"><strong>{{ formatRoi(totals.roi) }}</strong></td>
          <td>
            <span class="tier-list">{{ tiers.map((tier) => `¥${tier}`).join(' / ') }}</span>
          </td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { AllocationRow, StrategyTotals } from '../../types/strategy'
import { formatMoney, formatPercent, formatRoi } from '../../utils/formatNumber'
import { clusterColor } from '../../constants/clusterKinds'

withDefaults(
  defineProps<{
    allocations: AllocationRow[]
    totals?: StrategyTotals | null
    tiers?: number[]
  }>(),
  { totals: null, tiers: () => [] },
)
</script>

<style scoped>
.cluster-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.swatch {
  width: 9px;
  height: 9px;
  border-radius: 1px;
}
.face {
  font-family: var(--font-display);
  font-size: var(--step-1);
  font-weight: 500;
}
.tier-list {
  letter-spacing: 0.06em;
  color: var(--ink-2);
}
tfoot td {
  border-top: 1px solid var(--line-strong);
  border-bottom: 0;
  padding-top: 12px;
}
</style>
