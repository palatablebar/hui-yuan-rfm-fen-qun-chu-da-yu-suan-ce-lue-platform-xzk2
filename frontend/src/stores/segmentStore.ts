import { defineStore } from 'pinia'
import { createRun, fetchRun, fetchRunMembers, fetchRuns } from '../api/segment'
import type { Paginated } from '../types/api'
import type { RunDetail, RunSummary } from '../types/segment'
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
  }),
  getters: {
    completedRuns: (state): RunSummary[] => state.runs.filter((run) => run.status === 'completed'),
    latestCompleted: (state): RunSummary | null =>
      state.runs.find((run) => run.status === 'completed') ?? null,
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
        this.notice = `已提交分群任务 ${result.run.run_no}（${result.run.status}）`
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
    },
  },
})
