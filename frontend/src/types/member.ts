export interface MemberRow {
  id: number
  member_no: string
  name: string
  phone: string
  store_code: string
  store_name: string
  joined_at: string
  consent: boolean
}

export interface RunMemberRow {
  member_id: number
  member_no: string
  name: string
  phone: string
  store_code: string
  store_name: string
  consent: boolean
  recency_days: number
  frequency: number
  monetary: number
  r_score: number
  f_score: number
  m_score: number
  cluster_key: string
}

export interface StoreOption {
  store_code: string
  store_name: string
  member_count: number
}
