import type { ExportPreview, ExportResult, Strategy } from '../types/strategy'
import { http } from './http'

export function fetchStrategies(runId?: number): Promise<{ items: Strategy[] }> {
  const suffix = runId ? `?run_id=${runId}` : ''
  return http.get<{ items: Strategy[] }>(`/strategies${suffix}`)
}

export function fetchStrategy(strategyId: number): Promise<{ strategy: Strategy }> {
  return http.get<{ strategy: Strategy }>(`/strategies/${strategyId}`)
}

export function createStrategy(payload: {
  run_id: number
  name?: string
  total_budget: number
}): Promise<{ strategy: Strategy }> {
  return http.post<{ strategy: Strategy }>('/strategies', payload)
}

export function publishStrategy(strategyId: number, note?: string): Promise<{ strategy: Strategy }> {
  return http.post<{ strategy: Strategy }>(`/strategies/${strategyId}/publish`, { note })
}

export function previewExport(strategyId: number, clusterKey: string): Promise<ExportPreview> {
  const query = new URLSearchParams({ cluster_key: clusterKey })
  return http.get<ExportPreview>(`/strategies/${strategyId}/exports/preview?${query.toString()}`)
}

export function createExport(
  strategyId: number,
  payload: { cluster_key: string; channel: string; note?: string },
): Promise<ExportResult> {
  return http.post<ExportResult>(`/strategies/${strategyId}/exports`, payload)
}
