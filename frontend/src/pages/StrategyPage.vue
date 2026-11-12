<template>
  <div class="page">
    <PageHeader
      eyebrow="strategy · 券预算"
      title="触达预算与券面额"
      lede="每簇期望基准 = 历史券核销率 × 客单价 × 可触达人数；按基准排序分 40 / 25 / 15 三档券面额，保底 400 元/簇后按边际收益贪心分配预算。"
    >
      <template #actions>
        <RunSelector
          :runs="segmentStore.runs"
          :model-value="selectedRunId"
          @update:model-value="selectRun"
        />
      </template>
    </PageHeader>

    <div v-if="!auth.canWriteStrategy" class="notice" style="margin-bottom: 16px">
      当前角色只读策略。创建 / 发布策略需要 admin（运营主管），接口会返回 HTTP 403。
    </div>
    <div v-if="store.notice" class="notice ok" style="margin-bottom: 16px">{{ store.notice }}</div>
    <ErrorNotice v-if="store.error" :message="store.error" style="margin-bottom: 16px" @retry="reload" />

    <div v-if="run" class="grid-2">
      <div class="stack">
        <StrataPanel eyebrow="budget allocation · 参数与发布">
          <template #meta>
            <StatusTag v-if="current" kind="strategy" :value="current.status" />
          </template>
          <div class="budget-form">
            <div class="field">
              <label for="budget">本次触达预算（元）</label>
              <input
                id="budget"
                v-model.number="budget"
                class="input"
                type="number"
                min="1000"
                max="200000"
                step="500"
                data-testid="budget-input"
              />
            </div>
            <div class="field">
              <label for="strategy-name">策略名称（可选）</label>
              <input
                id="strategy-name"
                v-model="name"
                class="input"
                type="text"
                placeholder="如：11 月高价值沉睡唤醒"
              />
            </div>
            <button
              class="btn btn-accent"
              type="button"
              :disabled="!auth.canWriteStrategy || store.saving || !run"
              data-testid="allocate-button"
              @click="allocate"
            >
              {{ store.saving ? '计算中…' : '生成预算分配' }}
            </button>
          </div>

          <div v-if="current" class="strategy-meta" data-testid="strategy-totals">
            <div class="meta-line">
              <span class="eyebrow">策略</span>
              <strong>{{ current.strategy_no }}</strong>
              <span class="muted">{{ current.name }}</span>
            </div>
            <div class="totals">
              <div>
                <span class="eyebrow">预算</span>
                <b>{{ formatMoney(current.totals.budget) }}</b>
              </div>
              <div>
                <span class="eyebrow">预计核销券</span>
                <b>{{ current.totals.expected_redemptions.toFixed(1) }}</b>
              </div>
              <div>
                <span class="eyebrow">预计增量 GMV</span>
                <b>{{ formatMoney(current.totals.expected_gmv) }}</b>
              </div>
              <div>
                <span class="eyebrow">ROI</span>
                <b>{{ formatRoi(current.totals.roi) }}</b>
              </div>
              <div>
                <span class="eyebrow">券档位</span>
                <b>{{ current.tiers_used.map((tier) => `¥${tier}`).join(' / ') }}</b>
              </div>
            </div>
            <p class="muted policy">{{ current.totals.tier_policy }}</p>
            <div class="row">
              <button
                class="btn btn-primary"
                type="button"
                :disabled="!auth.canWriteStrategy || current.status === 'published' || store.saving"
                data-testid="publish-button"
                @click="publish"
              >
                {{ current.status === 'published' ? '已发布' : '发布到门店券核销' }}
              </button>
              <router-link class="btn" to="/outreach">去导出名单</router-link>
            </div>
          </div>
          <div v-else class="muted" style="margin-top: 14px">
            还没有策略。填预算（默认 8,000 元）后生成分配 —— 5 个簇各得券面额与预算，合计严格等于预算。
          </div>
        </StrataPanel>

        <StrataPanel eyebrow="strategy ledger · 该批次策略">
          <table class="data-table">
            <thead>
              <tr>
                <th>策略号</th>
                <th>预算</th>
                <th>券档</th>
                <th>状态</th>
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in store.items"
                :key="item.id"
                class="strategy-row"
                :class="{ active: current?.id === item.id }"
                @click="selectStrategy(item.id)"
              >
                <td>{{ item.strategy_no }}</td>
                <td class="num">{{ formatMoney(item.total_budget) }}</td>
                <td>{{ item.tiers_used.map((tier) => `¥${tier}`).join(' / ') }}</td>
                <td><StatusTag kind="strategy" :value="item.status" /></td>
                <td class="muted">{{ formatDateTime(item.created_at) }}</td>
              </tr>
              <tr v-if="!store.items.length">
                <td colspan="5" class="muted">该批次还没有策略。</td>
              </tr>
            </tbody>
          </table>
        </StrataPanel>
      </div>

      <StrataPanel eyebrow="cluster reference · 分配依据">
        <template #meta>
          <span>{{ run.clusters?.length ?? 0 }} 个簇</span>
        </template>
        <div class="layer-stack">
          <ClusterProfileCard
            v-for="cluster in run.clusters"
            :key="cluster.cluster_key"
            :cluster="cluster"
            :active="activeCluster === cluster.cluster_key"
            :show-advice="activeCluster === cluster.cluster_key"
            @select="activeCluster = $event"
          />
        </div>
        <p class="muted" style="margin-top: 12px; font-size: var(--step--1)">
          可触达人数来自会员授权字段；历史券核销率来自订单事实中的 coupon_issued / coupon_redeemed。
        </p>
      </StrataPanel>
    </div>

    <StrataPanel
      v-if="current"
      eyebrow="allocation table · 每簇预算与券建议"
      style="margin-top: 18px"
    >
      <template #meta>
        <span>预算合计 {{ formatMoney(current.totals.budget) }} · 严格等于输入预算</span>
      </template>
      <CouponBudgetTable
        :allocations="current.allocations"
        :totals="current.totals"
        :tiers="current.tiers_used"
      />
    </StrataPanel>

    <EmptyState
      v-if="!run && !segmentStore.loading"
      title="没有已完成的分群"
      text="先去分群总览跑一次 RFM 分群，再回来配置券预算。"
    />

    <p class="core-footer">
      <span>marginal greedy · 100 元步长</span>
      <span>保底 400 元/簇</span>
      <span style="margin-left: auto">budget {{ formatMoney(budget) }}</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import StrataPanel from '../components/common/StrataPanel.vue'
import RunSelector from '../components/common/RunSelector.vue'
import StatusTag from '../components/common/StatusTag.vue'
import ClusterProfileCard from '../components/common/ClusterProfileCard.vue'
import CouponBudgetTable from '../components/common/CouponBudgetTable.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useStrategyStore } from '../stores/strategyStore'
import { useSegmentStore } from '../stores/segmentStore'
import { useAuthStore } from '../stores/authStore'
import { DEFAULT_BUDGET } from '../constants/messages'
import { formatMoney, formatRoi } from '../utils/formatNumber'
import { formatDateTime } from '../utils/formatTime'

const store = useStrategyStore()
const segmentStore = useSegmentStore()
const auth = useAuthStore()

const selectedRunId = ref<number | null>(null)
const budget = ref(DEFAULT_BUDGET)
const name = ref('')
const activeCluster = ref('')

const run = computed(() => segmentStore.current)
const current = computed(() => store.current)

async function selectRun(runId: number) {
  selectedRunId.value = runId
  await loadRunContext(runId)
}

async function loadRunContext(runId: number) {
  store.current = null
  try {
    await segmentStore.loadRun(runId)
    activeCluster.value = segmentStore.current?.clusters?.[0]?.cluster_key ?? ''
    await store.loadStrategies(runId)
    if (store.items.length) await store.loadStrategy(store.items[0].id)
  } catch {
    /* handled */
  }
}

async function selectStrategy(strategyId: number) {
  try {
    await store.loadStrategy(strategyId)
  } catch {
    /* handled */
  }
}

async function allocate() {
  if (!selectedRunId.value) return
  try {
    await store.create(selectedRunId.value, budget.value, name.value.trim() || undefined)
    const match = store.current?.allocations?.[0]?.cluster_key
    if (match) activeCluster.value = match
    await store.loadStrategies(selectedRunId.value)
  } catch {
    /* handled */
  }
}

async function publish() {
  if (!current.value) return
  try {
    await store.publish(current.value.id, '11 月会员唤醒预算发布')
  } catch {
    /* handled */
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
    if (target) await selectRun(target)
  } catch {
    /* handled */
  }
})
</script>

<style scoped>
.budget-form {
  display: grid;
  grid-template-columns: 1.2fr 1.6fr auto;
  gap: 12px;
  align-items: end;
}
.strategy-meta {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
.meta-line {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.totals {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin: 12px 0;
}
.totals > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.totals b {
  font-family: var(--font-display);
  font-size: var(--step-1);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.policy {
  font-size: var(--step--1);
  margin-bottom: 12px;
}
.strategy-row {
  cursor: pointer;
}
.strategy-row.active {
  background: color-mix(in oklch, var(--sand-1) 60%, transparent);
}
@media (max-width: 980px) {
  .budget-form {
    grid-template-columns: 1fr;
  }
  .totals {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
