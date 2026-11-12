import { defineStore } from 'pinia'
import {
  activateRun,
  createRun,
  fetchReconciliation,
  fetchRun,
  fetchRunMembers,
  fetchRuns,
} from '../api/segment'
import type { Paginated } from '../types/api'
import type { Reconciliation, RunDetail, RunSummary } from '../types/segment'
import type { RunMemberRow } from '../types/member'

interface SegmentState {
  runs: RunSummary[]
  current: RunDetail | null
  currentId: number | null
  members: Paginated<RunMemberRow> | null
  membersLoading: boolean
  loading: boolean
  creating: boolean
  error: string
  notice: string
  reconciliation: Reconciliation | null
}

export const useSegmentStore = defineStore('segment', {
  state: (): SegmentState => ({
    runs: [],
    current: null,
    currentId: null,
    members: null,
    membersLoading: false,
    loading: false,
    creating: false,
    error: '',
    notice: '',
    reconciliation: null,
  }),
  getters: {
    completedRuns: (state): RunSummary[] => state.runs.filter((run) => run.status === 'completed'),
    latestCompleted: (state): RunSummary | null =>
      state.runs.find((run) => run.status === 'completed') ?? null,
    /** 当前版本（is_current=true）；没有任何批次成为当前版本时回退到最新完成批次。 */
    currentVersion: (state): RunSummary | null =>
      state.runs.find((run) => run.is_current) ??
      state.runs.find((run) => run.status === 'completed') ??
      null,
    clusters: (state) => state.current?.clusters ?? [],
    activeClusterKey: (state): string => {
      const list = state.current?.clusters ?? []
      return list[0]?.cluster_key ?? ''
    },
  },
  actions: {
    async loadRuns() {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchRuns()
        this.runs = result.items
        return result.items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载分群批次失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadRun(runId: number) {
      this.error = ''
      const result = await fetchRun(runId)
      this.current = result.run
      this.currentId = result.run.id
      return result.run
    },
    async runSegment(k = 'auto' as number | 'auto', asOf = '2026-11-12') {
      this.creating = true
      this.error = ''
      this.notice = ''
      try {
        const result = await createRun({ k, as_of: asOf })
        if (result.replayed) {
          // 同一补录重复运行：复用旧批次，不新增名单与触达、不重复占用预算
          this.notice = `输入未变化，已复用现有批次 ${result.run.run_no}，未新增名单与触达记录`
        } else {
          this.notice = result.run.is_current
            ? `新批次 ${result.run.run_no} 整批校验通过，已设为当前版本`
            : `批次 ${result.run.run_no} 已完成，但整批校验未通过，仍保留原当前版本`
        }
        await this.loadRuns()
        await this.loadRun(result.run.id)
        return result.run
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '创建分群失败'
        throw error
      } finally {
        this.creating = false
      }
    },
    async activate(runId: number) {
      this.error = ''
      try {
        const result = await activateRun(runId)
        this.notice = `已将 ${result.run.run_no} 切换为当前版本`
        await this.loadRuns()
        await this.loadRun(runId)
        return result.run
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '切换当前版本失败'
        throw error
      }
    },
    async loadReconciliation(runId: number) {
      this.reconciliation = await fetchReconciliation(runId)
      return this.reconciliation
    },
    async loadMembers(
      runId: number,
      params: { cluster_key?: string; search?: string; page?: number; page_size?: number } = {},
    ) {
      this.membersLoading = true
      try {
        this.members = await fetchRunMembers(runId, params)
        return this.members
      } finally {
        this.membersLoading = false
      }
    },
    clearCurrent() {
      this.current = null
      this.currentId = null
      this.members = null
      this.reconciliation = null
    },
  },
})
