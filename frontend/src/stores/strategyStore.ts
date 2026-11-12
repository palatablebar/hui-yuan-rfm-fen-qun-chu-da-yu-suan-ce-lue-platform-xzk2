import { defineStore } from 'pinia'
import {
  createExport,
  createStrategy,
  fetchStrategies,
  fetchStrategy,
  previewExport,
  publishStrategy,
} from '../api/strategy'
import type { AllocationRow, ExportPreview, Strategy } from '../types/strategy'

interface StrategyState {
  items: Strategy[]
  current: Strategy | null
  preview: ExportPreview | null
  loading: boolean
  saving: boolean
  error: string
  notice: string
}

export const useStrategyStore = defineStore('strategy', {
  state: (): StrategyState => ({
    items: [],
    current: null,
    preview: null,
    loading: false,
    saving: false,
    error: '',
    notice: '',
  }),
  getters: {
    allocations: (state): AllocationRow[] => state.current?.allocations ?? [],
    tiers: (state): number[] => state.current?.tiers_used ?? [],
    touchLog: (state) => (state.current?.touch_log ?? []).slice().reverse(),
  },
  actions: {
    async loadStrategies(runId?: number) {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchStrategies(runId)
        this.items = result.items
        if (!this.current && result.items.length) this.current = result.items[0]
        return result.items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载策略失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadStrategy(strategyId: number) {
      const result = await fetchStrategy(strategyId)
      this.current = result.strategy
      return result.strategy
    },
    async create(runId: number, totalBudget: number, name?: string) {
      this.saving = true
      this.error = ''
      this.notice = ''
      try {
        const result = await createStrategy({ run_id: runId, total_budget: totalBudget, name })
        this.current = result.strategy
        this.items = [result.strategy, ...this.items]
        this.notice = `已生成 ${result.strategy.strategy_no} 的预算分配`
        return result.strategy
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '生成策略失败'
        throw error
      } finally {
        this.saving = false
      }
    },
    async publish(strategyId: number, note?: string) {
      this.saving = true
      try {
        const result = await publishStrategy(strategyId, note)
        this.current = result.strategy
        this.items = this.items.map((item) =>
          item.id === result.strategy.id ? result.strategy : item,
        )
        this.notice = '策略已发布到门店券核销系统'
        return result.strategy
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '发布失败'
        throw error
      } finally {
        this.saving = false
      }
    },
    async loadPreview(strategyId: number, clusterKey: string) {
      this.preview = await previewExport(strategyId, clusterKey)
      return this.preview
    },
    async exportList(
      strategyId: number,
      clusterKey: string,
      channel = '企微',
      note?: string,
    ) {
      this.saving = true
      this.error = ''
      try {
        const result = await createExport(strategyId, { cluster_key: clusterKey, channel, note })
        if (this.current) {
          this.current = {
            ...this.current,
            touch_log: [...this.current.touch_log, result.entry],
            export_count: this.current.export_count + 1,
          }
        }
        this.notice = `已生成 ${result.entry.row_count} 行名单（${result.entry.id}）`
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '导出失败'
        throw error
      } finally {
        this.saving = false
      }
    },
  },
})
