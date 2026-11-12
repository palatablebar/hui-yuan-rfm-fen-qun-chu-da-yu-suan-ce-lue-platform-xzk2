export type SegmentStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface RunSummary {
  id: number
  run_no: string
  name: string
  status: SegmentStatus
  k_requested: string
  as_of: string
  random_state: number
  selected_k: number | null
  silhouette: number | null
  member_count: number | null
  cluster_count: number
  duration_ms: number | null
  error_message: string | null
  created_at: string | null
  completed_at: string | null
}

export interface ScoreMeans {
  r: number
  f: number
  m: number
}

export interface ClusterProfile {
  cluster_key: string
  kind: string
  label: string
  short: string
  advice: string
  member_count: number
  reachable_count: number
  gmv_total: number
  gmv_share: number
  gmv_per_member: number
  aov: number
  recency_mean_days: number
  frequency_mean: number
  monetary_mean: number
  coupon_issued: number
  coupon_redeemed: number
  redemption_rate: number
  expected_base: number
  score_means: ScoreMeans
}

export interface SilhouettePoint {
  k: number
  silhouette: number
  inertia: number
}

export interface ScoreDistribution {
  recency: number[]
  frequency: number[]
  monetary: number[]
}

export interface RawHistogram {
  edges: number[]
  counts: number[]
}

export interface Histograms {
  score_distribution: ScoreDistribution
  raw_distribution: Record<string, RawHistogram>
}

export interface ScatterPoint {
  member_no: string
  x: number
  y: number
  cluster_key: string
}

export interface RunDetail extends RunSummary {
  clusters?: ClusterProfile[]
  silhouette_curve?: SilhouettePoint[]
  histograms?: Histograms
  scatter?: ScatterPoint[]
  gmv_total?: number
  assignments_count?: number
  scoring_note?: string
}
