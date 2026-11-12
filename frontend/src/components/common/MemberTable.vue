<template>
  <div class="scroll-x">
    <table class="data-table">
      <thead>
        <tr>
          <th>会员编号</th>
          <th>姓名</th>
          <th>门店</th>
          <th class="num">R 天数</th>
          <th class="num">F 次数</th>
          <th class="num">M 累计</th>
          <th>R / F / M 分</th>
          <th>可触达</th>
          <th v-if="showCluster">所属簇</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.member_no">
          <td class="member-no">{{ row.member_no }}</td>
          <td>{{ row.name }}</td>
          <td>{{ row.store_name }}</td>
          <td class="num">{{ row.recency_days }}</td>
          <td class="num">{{ row.frequency }}</td>
          <td class="num">{{ formatMoney(row.monetary, 0) }}</td>
          <td>
            <span class="scores">
              <span class="score-chip" :data-score="row.r_score">{{ row.r_score }}</span>
              <span class="score-chip" :data-score="row.f_score">{{ row.f_score }}</span>
              <span class="score-chip" :data-score="row.m_score">{{ row.m_score }}</span>
            </span>
          </td>
          <td>
            <span class="consent" :class="{ off: !row.consent }">{{ row.consent ? '可触达' : '未授权' }}</span>
          </td>
          <td v-if="showCluster">{{ labelOf(row.cluster_key) }}</td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="showCluster ? 10 : 9" class="muted">没有符合条件的会员。</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { RunMemberRow } from '../../types/member'
import type { ClusterProfile } from '../../types/segment'
import { formatMoney } from '../../utils/formatNumber'

const props = withDefaults(
  defineProps<{
    rows: RunMemberRow[]
    clusters?: ClusterProfile[]
    showCluster?: boolean
  }>(),
  { clusters: () => [], showCluster: false },
)

function labelOf(key: string): string {
  const cluster = props.clusters.find((item) => item.cluster_key === key)
  return cluster ? `${key} ${cluster.label}` : key
}
</script>

<style scoped>
.data-table th,
.data-table td {
  white-space: nowrap;
}
.member-no {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
}
.scores {
  display: inline-flex;
  gap: 3px;
}
.consent {
  font-size: var(--step--1);
  color: var(--moss);
}
.consent.off {
  color: var(--ink-3);
}
</style>
