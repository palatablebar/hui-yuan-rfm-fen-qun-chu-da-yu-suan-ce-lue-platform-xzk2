<template>
  <div class="page">
    <PageHeader
      eyebrow="segments · rfm 分层"
      title="会员分层剖面"
      lede="R / F / M 等频五分位 → z-score 标准化 → numpy 手写 KMeans（k=3..8 用轮廓系数选最优）。每层是一个可解释的客群，人数与 GMV 占比都来自真实订单聚合。"
    >
      <template #actions>
        <RunSelector
          :runs="store.runs"
          :model-value="store.currentId"
          @update:model-value="selectRun"
        />
        <button
          class="btn btn-accent"
          type="button"
          :disabled="!auth.canRunSegment || store.creating"
          :title="auth.canRunSegment ? '以 2026-11-12 为 as-of 重跑 KMeans' : VIEWER_HINT"
          data-testid="run-segment-button"
          @click="runSegment"
        >
          {{ store.creating ? '提交中…' : '运行新分群' }}
        </button>
      </template>
    </PageHeader>

    <div v-if="!auth.canRunSegment" class="notice" style="margin-bottom: 18px">
      {{ VIEWER_HINT }} 只读模式下仍可查看全部簇画像与名单。
    </div>
    <div v-if="store.notice" class="notice ok" style="margin-bottom: 18px">{{ store.notice }}</div>
    <ErrorNotice
      v-if="store.error"
      :message="store.error"
      style="margin-bottom: 18px"
      @retry="reload"
    />

    <div v-if="run" class="kpi-strip" data-testid="segment-kpis">
      <div class="kpi">
        <div class="kpi-label">会员样本</div>
        <div class="kpi-value">{{ formatInt(run.member_count) }}<small>人</small></div>
        <div class="kpi-foot">as-of {{ run.as_of }} · random_state {{ run.random_state }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">入选 k</div>
        <div class="kpi-value">{{ run.selected_k }}<small>簇</small></div>
        <div class="kpi-foot">k 扫描 3–8，轮廓系数最大</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">平均轮廓系数</div>
        <div class="kpi-value">{{ formatSilhouette(run.silhouette) }}<small>s</small></div>
        <div class="kpi-foot">s = (b − a) / max(a, b)</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">簇数 / 可解释类型</div>
        <div class="kpi-value">{{ run.clusters?.length ?? 0 }}<small>类</small></div>
        <div class="kpi-foot">{{ run.clusters?.map((item) => item.short).join(' · ') }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">样本 GMV</div>
        <div class="kpi-value">{{ formatMoney(run.gmv_total) }}<small>元</small></div>
        <div class="kpi-foot">耗时 {{ formatDuration(run.duration_ms) }}</div>
      </div>
    </div>

    <div v-if="run" class="stack" style="margin-top: 20px">
      <div class="grid-2">
        <StrataPanel eyebrow="strata column · 簇剖面">
          <template #meta>
            <StatusTag kind="segment" :value="run.status" />
            <span>{{ run.run_no }}</span>
          </template>
          <div class="layer-stack" data-testid="cluster-layers">
            <ClusterProfileCard
              v-for="cluster in run.clusters"
              :key="cluster.cluster_key"
              :cluster="cluster"
              :active="activeCluster === cluster.cluster_key"
              :show-advice="activeCluster === cluster.cluster_key"
              @select="activeCluster = $event"
            />
          </div>
          <div v-if="activeClusterData" class="notice plain" style="margin-top: 16px">
            <span class="eyebrow">layer note</span>
            <span>
              {{ activeClusterData.label }}：人均 GMV {{ formatMoney(activeClusterData.gmv_per_member) }}，
              客单价 {{ formatMoney(activeClusterData.aov) }}，券核销率
              {{ formatPercent(activeClusterData.redemption_rate) }}。
            </span>
          </div>
          <div v-else-if="!run.clusters?.length" class="muted">暂无簇结果。</div>
        </StrataPanel>

        <div class="stack">
          <StrataPanel eyebrow="silhouette scan · 选 k 依据" tight>
            <SilhouetteCurve
              v-if="run.silhouette_curve?.length"
              :curve="run.silhouette_curve"
              :selected-k="run.selected_k"
            />
            <p class="muted" style="font-size: var(--step--1); margin-top: 6px">
              固定 random_state={{ run.random_state }}，同一批订单可复算；k={{ run.selected_k }} 的轮廓系数为
              {{ formatSilhouette(run.silhouette) }}。
            </p>
          </StrataPanel>
          <StrataPanel eyebrow="run log · 批次状态" tight>
            <div class="row" style="gap: 18px">
              <StatusTag kind="segment" :value="run.status" />
              <span class="muted">{{ formatDateTime(run.created_at) }}</span>
              <span class="muted">耗时 {{ formatDuration(run.duration_ms) }}</span>
            </div>
            <p v-if="run.status === 'queued' || run.status === 'running'" class="muted" style="margin-top: 8px">
              Worker 正在计算，页面每 1.2s 自动刷新。
            </p>
            <p v-if="run.error_message" class="muted" style="margin-top: 8px; color: var(--danger)">
              {{ run.error_message }}
            </p>
          </StrataPanel>
        </div>
      </div>

      <StrataPanel eyebrow="scatter · R 距今天数 × M 累计消费">
        <template #meta>
          <span>{{ run.scatter?.length ?? 0 }} 个抽样点</span>
        </template>
        <ClusterScatter
          v-if="run.scatter?.length && run.clusters?.length"
          :points="run.scatter"
          :clusters="run.clusters"
        />
      </StrataPanel>
    </div>

    <EmptyState
      v-else-if="!store.loading"
      title="还没有可看的分群剖面"
      text="用 as-of 2026-11-12 跑一次分群：后端会聚合 2,400 条订单事实，做五分位打分与 KMeans。"
    >
      <button class="btn btn-primary" type="button" :disabled="!auth.canRunSegment" @click="runSegment">
        运行第一次分群
      </button>
    </EmptyState>

    <p class="core-footer">
      <span>拾光咖啡会员运营</span>
      <span>numpy k-means · silhouette</span>
      <span style="margin-left: auto">stratum depth 0–600</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import StrataPanel from '../components/common/StrataPanel.vue'
import RunSelector from '../components/common/RunSelector.vue'
import StatusTag from '../components/common/StatusTag.vue'
import ClusterProfileCard from '../components/common/ClusterProfileCard.vue'
import ClusterScatter from '../components/common/ClusterScatter.vue'
import SilhouetteCurve from '../components/common/SilhouetteCurve.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useSegmentStore } from '../stores/segmentStore'
import { useAuthStore } from '../stores/authStore'
import { useRunPolling } from '../hooks/useRunPolling'
import { VIEWER_HINT } from '../constants/messages'
import {
  formatInt,
  formatMoney,
  formatPercent,
  formatSilhouette,
} from '../utils/formatNumber'
import { formatDateTime, formatDuration } from '../utils/formatTime'

const store = useSegmentStore()
const auth = useAuthStore()
const activeCluster = ref('')

const run = computed(() => store.current)
const activeClusterData = computed(() =>
  (run.value?.clusters ?? []).find((cluster) => cluster.cluster_key === activeCluster.value),
)

useRunPolling(() => store.currentId)

async function selectRun(runId: number) {
  await loadRun(runId)
}

async function loadRun(runId: number) {
  try {
    const detail = await store.loadRun(runId)
    if (!activeCluster.value || !detail.clusters?.some((item) => item.cluster_key === activeCluster.value)) {
      activeCluster.value = detail.clusters?.[0]?.cluster_key ?? ''
    }
  } catch {
    /* store.error 已记录 */
  }
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

async function runSegment() {
  try {
    const created = await store.runSegment('auto', '2026-11-12')
    await loadRun(created.id)
    activeCluster.value = ''
  } catch {
    /* store.error 已记录 */
  }
}

onMounted(async () => {
  try {
    await store.loadRuns()
    const target = store.currentId ?? store.latestCompleted?.id ?? store.runs[0]?.id
    if (target) await loadRun(target)
  } catch {
    /* handled */
  }
})

watch(
  () => store.current?.status,
  (status) => {
    if (status === 'completed') store.loadRuns().catch(() => undefined)
  },
)
</script>
