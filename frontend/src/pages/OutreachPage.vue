<template>
  <div class="page">
    <PageHeader
      eyebrow="outreach · 名单与触达"
      title="名单导出与触达记录"
      lede="从已发布策略里选簇，导出该簇会员名单 CSV；每次导出都会写一条触达记录（操作人 / 渠道 / 行数），店长只读可下载、不可导出。"
    >
      <template #actions>
        <RunSelector :runs="segmentStore.runs" :model-value="selectedRunId" @update:model-value="selectRun" />
        <select
          v-if="strategies.length"
          v-model.number="selectedStrategyId"
          class="select"
          data-testid="strategy-select"
          @change="onStrategyChange"
        >
          <option v-for="item in strategies" :key="item.id" :value="item.id">
            {{ item.strategy_no }} · {{ statusLabel(item.status) }}
          </option>
        </select>
      </template>
    </PageHeader>

    <div v-if="!auth.canExport" class="notice" style="margin-bottom: 16px">
      店长角色只读：可查看并与下载已有名单，但不能创建导出（POST /strategies/{id}/exports 返回 403）。
    </div>
    <div v-if="store.notice" class="notice ok" style="margin-bottom: 16px">{{ store.notice }}</div>
    <ErrorNotice v-if="store.error" :message="store.error" style="margin-bottom: 16px" @retry="reload" />

    <div v-if="strategy && run" class="grid-2">
      <div class="stack">
        <StrataPanel eyebrow="export · 生成名单">
          <div v-if="preview" class="preview" data-testid="export-preview">
            <div class="preview-main">
              <span class="eyebrow">预计名单行数</span>
              <div class="display preview-count">{{ preview.row_count }}<small> 行</small></div>
              <p class="muted">
                {{ preview.cluster_key }} · {{ preview.cluster_label }} · 可触达
                {{ preview.reachable_count }} 人 · 券面额
                {{ preview.coupon_face ? `¥${preview.coupon_face}` : '—' }}
              </p>
            </div>
            <div class="preview-side">
              <div class="field">
                <label for="channel">触达渠道</label>
                <select id="channel" v-model="channel" class="select">
                  <option>企微</option>
                  <option>短信</option>
                  <option>门店券核销</option>
                </select>
              </div>
              <button
                class="btn btn-accent"
                type="button"
                :disabled="!auth.canExport || store.saving"
                data-testid="export-button"
                @click="doExport"
              >
                {{ store.saving ? '生成中…' : '导出 CSV 名单' }}
              </button>
            </div>
          </div>
          <div v-else class="muted">选择簇后显示预计行数。</div>
          <div v-if="latestExportId && strategy" class="row" style="margin-top: 14px">
            <button class="btn btn-sm" type="button" data-testid="download-latest" @click="download(latestExportId)">
              下载最新名单 {{ latestExportId }}
            </button>
            <span class="muted">CSV 含 R/F/M 分数与券面额建议</span>
          </div>
        </StrataPanel>

        <StrataPanel eyebrow="choose layer · 选择导出簇">
          <template #meta>
            <span>{{ strategy.strategy_no }}</span>
          </template>
          <div class="layer-stack" data-testid="export-clusters">
            <ClusterProfileCard
              v-for="cluster in run.clusters"
              :key="cluster.cluster_key"
              :cluster="cluster"
              :active="clusterKey === cluster.cluster_key"
              @select="selectCluster"
            />
          </div>
        </StrataPanel>
      </div>

      <StrataPanel eyebrow="member preview · 名单预览（前 15 行）">
        <template #meta>
          <span>{{ clusterKey }}</span>
        </template>
        <MemberTable v-if="segmentStore.members" :rows="segmentStore.members.items" :clusters="run.clusters" />
        <p v-if="segmentStore.members" class="muted" style="margin-top: 8px">
          该簇共 {{ segmentStore.members.total }} 人（含未授权触达的会员，导出时一并列明）。
        </p>
      </StrataPanel>
    </div>

    <StrataPanel v-if="strategy" eyebrow="touch log · 导出与发布记录" style="margin-top: 18px">
      <template #meta>
        <span>{{ strategy.touch_log.length }} 条</span>
      </template>
      <table class="data-table" data-testid="touch-log">
        <thead>
          <tr>
            <th>记录</th>
            <th>类型</th>
            <th>簇 / 说明</th>
            <th>渠道</th>
            <th class="num">行数</th>
            <th>操作人</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in reversedLog" :key="entry.id">
            <td>{{ entry.id }}</td>
            <td>{{ entry.kind === 'export' ? '名单导出' : entry.kind === 'publish' ? '策略发布' : entry.kind }}</td>
            <td>{{ entry.cluster_key ? `${entry.cluster_key} · ${entry.cluster_label}` : entry.note }}</td>
            <td>{{ entry.channel }}</td>
            <td class="num">{{ entry.row_count }}</td>
            <td>{{ entry.created_by || '—' }}</td>
            <td class="muted">{{ formatDateTime(entry.created_at) }}</td>
            <td>
              <button
                v-if="entry.kind === 'export'"
                class="btn btn-sm"
                type="button"
                :data-testid="`download-${entry.id}`"
                @click="download(entry.id)"
              >
                下载 CSV
              </button>
              <span v-else class="muted">—</span>
            </td>
          </tr>
          <tr v-if="!strategy.touch_log.length">
            <td colspan="8" class="muted">还没有导出记录。选择簇后点「导出 CSV 名单」。</td>
          </tr>
        </tbody>
      </table>
    </StrataPanel>

    <EmptyState
      v-if="!strategy && !store.loading"
      title="还没有可导出的策略"
      text="先到策略配置页为某次分群生成券预算（默认 8,000 元），再回来导出「高价值沉睡」名单。"
    >
      <router-link class="btn btn-primary" to="/strategy">去配置策略</router-link>
    </EmptyState>

    <p class="core-footer">
      <span>csv · utf-8 bom</span>
      <span>导出写入 touch_log</span>
      <span style="margin-left: auto">{{ strategy?.strategy_no ?? '—' }}</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import StrataPanel from '../components/common/StrataPanel.vue'
import RunSelector from '../components/common/RunSelector.vue'
import ClusterProfileCard from '../components/common/ClusterProfileCard.vue'
import MemberTable from '../components/common/MemberTable.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useStrategyStore } from '../stores/strategyStore'
import { useSegmentStore } from '../stores/segmentStore'
import { useAuthStore } from '../stores/authStore'
import { downloadFile } from '../utils/request'
import { formatDateTime } from '../utils/formatTime'
import { STRATEGY_STATUS_META } from '../constants/strategyStatus'
import type { StrategyStatus } from '../types/strategy'

function statusLabel(status: StrategyStatus): string {
  return STRATEGY_STATUS_META[status]?.label ?? status
}

const store = useStrategyStore()
const segmentStore = useSegmentStore()
const auth = useAuthStore()

const selectedRunId = ref<number | null>(null)
const selectedStrategyId = ref<number | null>(null)
const clusterKey = ref('')
const channel = ref('企微')
const latestExportId = ref('')

const run = computed(() => segmentStore.current)
const strategy = computed(() => store.current)
const strategies = computed(() => store.items)
const preview = computed(() => store.preview)
const reversedLog = computed(() => (strategy.value?.touch_log ?? []).slice().reverse())

async function selectRun(runId: number) {
  selectedRunId.value = runId
  await loadContext(runId)
}

async function loadContext(runId: number) {
  selectedRunId.value = runId
  store.current = null
  store.preview = null
  latestExportId.value = ''
  try {
    await segmentStore.loadRun(runId)
    await store.loadStrategies(runId)
    if (!store.items.length) return
    selectedStrategyId.value = store.items[0].id
    const loaded = await store.loadStrategy(store.items[0].id)
    const lastExport = [...(loaded.touch_log || [])].reverse().find((entry) => entry.kind === 'export')
    latestExportId.value = lastExport?.id ?? ''
    const clusters = segmentStore.current?.clusters ?? []
    const dormant = clusters.find((item) => item.kind === 'HIGH_VALUE_DORMANT')
    clusterKey.value = dormant?.cluster_key ?? clusters[0]?.cluster_key ?? ''
    await onClusterChange()
  } catch {
    /* handled */
  }
}

async function onStrategyChange() {
  if (!selectedStrategyId.value) return
  try {
    await store.loadStrategy(selectedStrategyId.value)
    await onClusterChange()
  } catch {
    /* handled */
  }
}

async function selectCluster(key: string) {
  clusterKey.value = key
  await onClusterChange()
}

async function onClusterChange() {
  if (!strategy.value || !clusterKey.value) return
  try {
    await store.loadPreview(strategy.value.id, clusterKey.value)
    if (selectedRunId.value) {
      await segmentStore.loadMembers(selectedRunId.value, {
        cluster_key: clusterKey.value,
        page_size: 15,
      })
    }
  } catch {
    /* handled */
  }
}

async function doExport() {
  if (!strategy.value) return
  try {
    const result = await store.exportList(strategy.value.id, clusterKey.value, channel.value)
    latestExportId.value = result.entry.id
    await store.loadPreview(strategy.value.id, clusterKey.value)
  } catch {
    /* handled */
  }
}

async function download(exportId: string) {
  if (!strategy.value) return
  try {
    await downloadFile(
      `/strategies/${strategy.value.id}/exports/${exportId}/download`,
      `${strategy.value.strategy_no}_${clusterKey.value}_${exportId}.csv`,
    )
  } catch (error) {
    store.error = (error as { message?: string }).message ?? '下载失败'
  }
}

async function reload() {
  try {
    await segmentStore.loadRuns()
    const target = selectedRunId.value ?? segmentStore.latestCompleted?.id
    if (target) await selectRun(target)
  } catch {
    /* handled */
  }
}

onMounted(async () => {
  try {
    await segmentStore.loadRuns()
    const target = segmentStore.latestCompleted?.id ?? segmentStore.runs[0]?.id
    if (target) await loadContext(target)
  } catch {
    /* handled */
  }
})
</script>

<style scoped>
.preview {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 22px;
  align-items: end;
}
.preview-count {
  font-size: var(--step-5);
  line-height: 0.95;
  margin: 4px 0 6px;
}
.preview-count small {
  font-family: var(--font-body);
  font-size: var(--step-1);
  color: var(--ink-3);
  letter-spacing: 0.06em;
}
.preview-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
@media (max-width: 980px) {
  .preview {
    grid-template-columns: 1fr;
  }
}
</style>
