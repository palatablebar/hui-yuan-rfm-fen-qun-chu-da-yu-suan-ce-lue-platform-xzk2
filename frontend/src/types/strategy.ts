export type StrategyStatus = 'draft' | 'published' | 'archived'

export interface AllocationRow {
  cluster_key: string
  label: string
  kind: string
  member_count: number
  reachable_count: number
  redemption_rate: number
  aov: number
  expected_base: number
  coupon_face: number
  budget: number
  budget_share: number
  coupon_count: number
  redeemable_coupons: number
  expected_redemptions: number
  expected_gmv: number
  roi: number
  saturation: number
  tier_rank: number
}

export interface StrategyTotals {
  budget: number
  expected_redemptions: number
  expected_gmv: number
  roi: number
  reachable_members: number
  member_count: number
  tier_policy?: string
  step?: number
}

export interface TouchEntry {
  id: string
  kind: 'export' | 'publish' | string
  cluster_key?: string
  cluster_label?: string
  channel: string
  note: string
  row_count: number
  created_by?: string | null
  created_at: string
}

export interface Strategy {
  id: number
  strategy_no: string
  name: string
  status: StrategyStatus
  run_id: number
  run_no: string | null
  run_as_of: string | null
  selected_k: number | null
  silhouette: number | null
  total_budget: number
  allocations: AllocationRow[]
  totals: StrategyTotals
  tiers_used: number[]
  touch_log: TouchEntry[]
  export_count: number
  created_at: string | null
  updated_at: string | null
  published_at: string | null
}

export interface ExportPreview {
  cluster_key: string
  cluster_label: string
  row_count: number
  reachable_count: number
  coupon_face: number | null
  budget: number | null
}

export interface ExportResult {
  entry: TouchEntry
  download_url: string
}
