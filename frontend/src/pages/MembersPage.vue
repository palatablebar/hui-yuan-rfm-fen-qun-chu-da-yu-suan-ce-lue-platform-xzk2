<template>
  <div class="page">
    <PageHeader
      eyebrow="rfm ledger · 会员明细"
      title="RFM 明细与分数分布"
      lede="每个会员的 R（距今）、F（订单数）、M（累计消费）与五分位分数；点击簇切换名单。所有数值由后端从订单事实聚合，前端只做呈现。"
    >
      <template #actions>
        <RunSelector :runs="store.runs" :model-value="store.currentId" @update:model-value="selectRun" />
      </template>
    </PageHeader>

    <ErrorNotice v-if="store.error" :message="store.error" style="margin-bottom: 16px" @retry="reload" />

    <div v-if="run" class="run-brief">
      <div class="brief-cell">
        <span class="eyebrow">批次</span>
        <strong>{{ run.run_no }}</strong>
      </div>
      <div class="brief-cell">
        <span class="eyebrow">as-of</span>
        <strong>{{ run.as_of }}</strong>
      </div>
      <div class="brief-cell">
        <span class="eyebrow">k / 轮廓</span>
        <strong>{{ run.selected_k }} / {{ formatSilhouette(run.silhouette) }}</strong>
      </div>
      <div class="brief-cell">
        <span class="eyebrow">样本</span>
        <strong>{{ formatInt(run.member_count) }} 人</strong>
      </div>
      <div class="brief-cell stores">
        <span class="eyebrow">门店基数</span>
        <span class="store-chips">
          <span
            v-for="storeItem in memberStore.stores"
            :key="storeItem.store_code"
            class="tag"
            :title="storeOrderTitle(storeItem.store_code)"
          >
            {{ storeItem.store_name }} {{ storeItem.member_count }}
          </span>
        </span>
      </div>
    </div>

    <div class="cluster-chips" v-if="run?.clusters?.length">
      <button
        v-for="cluster in run.clusters"
        :key="cluster.cluster_key"
        type="button"
        class="cluster-chip"
        :class="{ active: cluster.cluster_key === clusterKey }"
        :data-testid="`chip-${cluster.cluster_key}`"
        @click="selectCluster(cluster.cluster_key)"
      >
        <span class="dot" :style="{ background: clusterColor(cluster.kind) }" />
        <span>{{ cluster.cluster_key }} · {{ cluster.label }}</span>
        <b>{{ cluster.member_count }}</b>
      </button>
    </div>

    <div v-if="run?.histograms" class="grid-2" style="margin-top: 18px">
      <StrataPanel eyebrow="score distribution · 五分位直方图">
        <template #meta>
          <span>每档约 120 人 · R 已反向</span>
        </template>
        <ScoreHistogram :histograms="run.histograms" />
      </StrataPanel>
      <StrataPanel eyebrow="layer reading · 当前簇">
        <template #meta>
          <span>{{ clusterKey }}</span>
        </template>
        <div v-if="activeCluster" class="cluster-readout">
          <div class="display" style="font-size: var(--step-2)">{{ activeCluster.label }}</div>
          <p class="muted" style="margin-top: 6px">{{ activeCluster.advice }}</p>
          <dl class="readout-grid">
            <div><dt>人数</dt><dd>{{ activeCluster.member_count }}</dd></div>
            <div><dt>可触达</dt><dd>{{ activeCluster.reachable_count }}</dd></div>
            <div><dt>R 均值</dt><dd>{{ activeCluster.recency_mean_days }} 天</dd></div>
            <div><dt>F 均值</dt><dd>{{ activeCluster.frequency_mean }} 次</dd></div>
            <div><dt>M 均值</dt><dd>{{ formatMoney(activeCluster.monetary_mean) }}</dd></div>
            <div><dt>券核销率</dt><dd>{{ formatPercent(activeCluster.redemption_rate) }}</dd></div>
          </dl>
        </div>
      </StrataPanel>
    </div>

    <StrataPanel eyebrow="member table · 当前簇名单" style="margin-top: 18px">
      <template #meta>
        <input
          v-model="search"
          class="input"
          type="search"
          placeholder="搜索会员编号 / 姓名 / 手机"
          style="width: 250px"
          data-testid="member-search"
          @keyup.enter="applySearch"
        />
        <button class="btn btn-sm" type="button" @click="applySearch">筛选</button>
      </template>
      <MemberTable v-if="store.members" :rows="store.members.items" :clusters="run?.clusters" />
      <div class="row" style="margin-top: 12px" data-testid="member-pager">
        <span class="muted">
          共 {{ store.members?.total ?? 0 }} 人 · 第 {{ store.members?.page ?? 1 }} / {{ store.members?.pages || 1 }} 页
        </span>
        <span class="spacer" />
        <button class="btn btn-sm" type="button" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <button class="btn btn-sm" type="button" :disabled="page >= (store.members?.pages || 1)" @click="goPage(page + 1)">下一页</button>
      </div>
    </StrataPanel>

    <EmptyState
      v-if="!run && !store.loading"
      title="没有可读的批次"
      text="先在分群总览跑一次 RFM 分群，再回来看分数分布与会员明细。"
    />

    <p class="core-footer">
      <span>订单事实 {{ orderStore.totals?.orders ?? '—' }} 条</span>
      <span>券核销率 {{ formatPercent(orderStore.totals?.redemption_rate) }}</span>
      <span>等频五分位 · z-score</span>
      <span style="margin-left: auto">page {{ page }}</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import StrataPanel from '../components/common/StrataPanel.vue'
import RunSelector from '../components/common/RunSelector.vue'
import ScoreHistogram from '../components/common/ScoreHistogram.vue'
import MemberTable from '../components/common/MemberTable.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useSegmentStore } from '../stores/segmentStore'
import { useMemberStore } from '../stores/memberStore'
import { useOrderStore } from '../stores/orderStore'
import { clusterColor } from '../constants/clusterKinds'
import {
  formatInt,
  formatMoney,
  formatPercent,
  formatSilhouette,
} from '../utils/formatNumber'

const store = useSegmentStore()
const memberStore = useMemberStore()
const orderStore = useOrderStore()

function storeOrderTitle(storeCode: string): string {
  const stat = orderStore.byStore[storeCode]
  if (!stat) return '订单事实加载中'
  return `订单 ${stat.orders} 笔 · GMV ${formatMoney(stat.gmv)} · 券核销率 ${formatPercent(stat.redemption_rate)}`
}

const clusterKey = ref('')
const search = ref('')
const page = ref(1)
const run = computed(() => store.current)
const activeCluster = computed(() =>
  (run.value?.clusters ?? []).find((cluster) => cluster.cluster_key === clusterKey.value),
)

async function loadMembers() {
  if (!store.currentId || !clusterKey.value) return
  await store.loadMembers(store.currentId, {
    cluster_key: clusterKey.value,
    search: search.value || undefined,
    page: page.value,
    page_size: 12,
  })
}

async function loadRun(runId: number) {
  try {
    const detail = await store.loadRun(runId)
    const target =
      detail.clusters?.find((cluster) => cluster.cluster_key === clusterKey.value)?.cluster_key ??
      detail.clusters?.[0]?.cluster_key ??
      ''
    clusterKey.value = target
    page.value = 1
    await loadMembers()
  } catch {
    /* handled by store.error */
  }
}

async function selectRun(runId: number) {
  await loadRun(runId)
}

async function selectCluster(key: string) {
  clusterKey.value = key
  page.value = 1
  await loadMembers()
}

function applySearch() {
  page.value = 1
  loadMembers().catch(() => undefined)
}

async function goPage(next: number) {
  page.value = next
  await loadMembers()
}

async function reload() {
  try {
    await store.loadRuns()
    const target = store.currentId ?? store.latestCompleted?.id
    if (target) await loadRun(target)
  } catch {
    /* handled */
  }
}

onMounted(async () => {
  memberStore.loadStores().catch(() => undefined)
  orderStore.loadSummary().catch(() => undefined)
  try {
    await store.loadRuns()
    const target = store.currentId ?? store.latestCompleted?.id ?? store.runs[0]?.id
    if (target) await loadRun(target)
  } catch {
    /* handled */
  }
})
</script>

<style scoped>
.run-brief {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, auto)) minmax(0, 1fr);
  gap: 0;
  border: 1px solid var(--line-strong);
  margin-bottom: 16px;
}
.brief-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 11px 16px;
  border-right: 1px solid var(--line);
  min-width: 0;
}
.brief-cell:last-child {
  border-right: 0;
}
.brief-cell strong {
  font-family: var(--font-display);
  font-size: var(--step-1);
  font-weight: 500;
  white-space: nowrap;
}
.brief-cell.stores {
  min-width: 0;
}
.store-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.cluster-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cluster-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border: 1px solid var(--line-strong);
  background: var(--paper);
  border-radius: var(--radius);
  font-size: var(--step--1);
  color: var(--ink-2);
}
.cluster-chip:hover {
  border-color: var(--ink-2);
}
.cluster-chip.active {
  border-color: var(--rust);
  color: var(--ink);
  background: color-mix(in oklch, var(--sand-1) 58%, var(--paper));
}
.cluster-chip .dot {
  width: 8px;
  height: 8px;
  border-radius: 1px;
}
.cluster-chip b {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.cluster-readout .readout-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 22px;
  margin: 14px 0 0;
}
.readout-grid dt {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.readout-grid dd {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: var(--step-1);
  font-variant-numeric: tabular-nums;
}
@media (max-width: 980px) {
  .run-brief {
    grid-template-columns: 1fr 1fr;
  }
  .brief-cell {
    border-bottom: 1px solid var(--line);
  }
  .brief-cell.stores {
    grid-column: span 2;
  }
}
</style>
