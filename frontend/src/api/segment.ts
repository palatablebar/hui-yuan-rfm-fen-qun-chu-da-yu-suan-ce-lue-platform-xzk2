import type { Paginated } from '../types/api'
import type { RunDetail, RunSummary } from '../types/segment'
import type { RunMemberRow } from '../types/member'
import { http } from './http'

export function fetchRuns(limit = 20): Promise<{ items: RunSummary[] }> {
  return http.get<{ items: RunSummary[] }>(`/segments/runs?limit=${limit}`)
}

export function fetchRun(runId: number): Promise<{ run: RunDetail }> {
  return http.get<{ run: RunDetail }>(`/segments/runs/${runId}`)
}

export function createRun(payload: {
  k: number | 'auto'
  as_of?: string
  name?: string
}): Promise<{ run: RunSummary }> {
  return http.post<{ run: RunSummary }>('/segments/runs', payload)
}

export function fetchRunMembers(
  runId: number,
  params: { cluster_key?: string; search?: string; page?: number; page_size?: number },
): Promise<Paginated<RunMemberRow>> {
  const query = new URLSearchParams()
  if (params.cluster_key) query.set('cluster_key', params.cluster_key)
  if (params.search) query.set('search', params.search)
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 20))
  return http.get<Paginated<RunMemberRow>>(`/segments/runs/${runId}/members?${query.toString()}`)
}
