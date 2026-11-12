<template>
  <StrataPanel eyebrow="batch version · 批次版本与三方对账">
    <template #meta>
      <span v-if="run.is_current" class="tag" data-tone="ok" data-testid="current-badge">
        <span class="tag-dot" />当前版本
      </span>
      <span v-else class="tag" data-tone="muted">历史版本</span>
      <StatusTag kind="segment" :value="run.status" />
    </template>

    <div class="version-grid">
      <div class="version-meta">
        <div class="meta-row"><span class="eyebrow">批次号</span><strong>{{ run.run_no }}</strong></div>
        <div class="meta-row"><span class="eyebrow">统计日 as-of</span><span>{{ run.as_of }}</span></div>
        <div class="meta-row">
          <span class="eyebrow">输入指纹</span>
          <code class="fingerprint" :title="run.input_fingerprint ?? ''">
            {{ run.input_fingerprint ? run.input_fingerprint.slice(0, 16) + '…' : '—' }}
          </code>
        </div>
        <div class="meta-row">
          <span class="eyebrow">成为当前版本</span>
          <span>{{ run.current_since ? formatDateTime(run.current_since) : '未成为当前版本' }}</span>
        </div>
        <button
          v-if="!run.is_current && canActivate && run.validation_ok"
          class="btn btn-sm btn-primary"
          type="button"
          data-testid="activate-button"
          :disabled="activating"
          @click="emit('activate', run.id)"
        >
          {{ activating ? '切换中…' : '切换为当前版本' }}
        </button>
        <p v-if="!run.validation_ok && run.status === 'completed'" class="muted danger-text">
          整批校验未通过：该批次不会成为当前版本，线上仍展示原版本。
        </p>
      </div>

      <div v-if="reconciliation" class="recon" data-testid="reconciliation">
        <div class="recon-totals">
          <div class="recon-cell">
            <span class="eyebrow">会员（库 / 名单）</span>
            <b :class="{ mismatch: !memberMatch }">
              {{ reconciliation.totals.members_in_db }} / {{ reconciliation.totals.assignments }}
            </b>
          </div>
          <div class="recon-cell">
            <span class="eyebrow">订单事实</span>
            <b>{{ formatInt(reconciliation.totals.orders_in_db) }}</b>
            <small>GMV {{ formatMoney(reconciliation.totals.order_gmv) }}</small>
          </div>
          <div class="recon-cell">
            <span class="eyebrow">簇人数加总</span>
            <b :class="{ mismatch: !clusterSumMatch }">
              {{ reconciliation.totals.cluster_profile_sum }} / {{ reconciliation.totals.assignments }}
            </b>
          </div>
          <div class="recon-cell">
            <span class="eyebrow">可触达合计</span>
            <b>{{ formatInt(reconciliation.totals.reachable_sum) }}</b>
          </div>
        </div>

        <table class="data-table recon-table">
          <thead>
            <tr>
              <th>簇</th>
              <th class="num">画像人数</th>
              <th class="num">名单人数</th>
              <th class="num">可触达</th>
              <th>对得上</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in reconciliation.clusters" :key="row.cluster_key">
              <td>{{ row.cluster_key }} · {{ row.label }}</td>
              <td class="num">{{ row.profile_member_count }}</td>
              <td class="num">{{ row.assignment_count }}</td>
              <td class="num">{{ row.reachable_count }}</td>
              <td>
                <span :class="row.match ? 'ok-text' : 'danger-text'">
                  {{ row.match ? '✓ 一致' : '✗ 不一致' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="check-list">
          <span
            v-for="check in reconciliation.checks"
            :key="check.name"
            class="check-chip"
            :class="check.ok ? 'ok-text' : 'danger-text'"
            :title="check.detail ?? undefined"
          >
            {{ check.ok ? '✓' : '✗' }} {{ checkLabel(check.name) }}
          </span>
        </div>
      </div>
      <div v-else class="muted">对账数据加载中…</div>
    </div>
  </StrataPanel>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StrataPanel from './StrataPanel.vue'
import StatusTag from './StatusTag.vue'
import type { Reconciliation, RunDetail } from '../../types/segment'
import { formatInt, formatMoney } from '../../utils/formatNumber'
import { formatDateTime } from '../../utils/formatTime'

const props = defineProps<{
  run: RunDetail
  reconciliation: Reconciliation | null
  canActivate: boolean
  activating?: boolean
}>()

const emit = defineEmits<{ activate: [runId: number] }>()

const memberMatch = computed(
  () =>
    !!props.reconciliation &&
    props.reconciliation.totals.members_in_db === props.reconciliation.totals.assignments &&
    props.reconciliation.totals.members_in_db === props.reconciliation.totals.members_in_run,
)
const clusterSumMatch = computed(
  () =>
    !!props.reconciliation &&
    props.reconciliation.totals.cluster_profile_sum === props.reconciliation.totals.assignments,
)

const CHECK_LABELS: Record<string, string> = {
  result_snapshot: '结果快照',
  member_coverage: '会员覆盖',
  order_ownership: '订单归属',
  cluster_member_sum: '簇人数加总',
  cluster_assignment_detail: '簇内明细',
  cluster_reachable_detail: '可触达人数',
}

function checkLabel(name: string): string {
  return CHECK_LABELS[name] ?? name
}
</script>

<style scoped>
.version-grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 22px;
}
.version-meta {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.meta-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.fingerprint {
  font-size: var(--step--1);
  background: color-mix(in oklch, var(--sand-1) 70%, transparent);
  padding: 2px 6px;
  border-radius: 4px;
}
.recon-totals {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.recon-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.recon-cell b {
  font-family: var(--font-display);
  font-size: var(--step-1);
  font-variant-numeric: tabular-nums;
}
.recon-cell small {
  color: var(--ink-3);
}
.mismatch {
  color: var(--danger);
}
.recon-table {
  margin-bottom: 12px;
}
.check-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.check-chip {
  font-size: var(--step--1);
  padding: 3px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
}
.ok-text {
  color: var(--ok);
}
.danger-text {
  color: var(--danger);
}
@media (max-width: 980px) {
  .version-grid {
    grid-template-columns: 1fr;
  }
  .recon-totals {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
