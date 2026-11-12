export interface OrderStoreStat {
  store_code: string
  store_name: string
  orders: number
  gmv: number
  coupon_issued: number
  coupon_redeemed: number
  redemption_rate: number
}

export interface OrderTotals {
  orders: number
  gmv: number
  coupon_issued: number
  coupon_redeemed: number
  redemption_rate: number
}

export interface OrderSummary {
  totals: OrderTotals
  stores: OrderStoreStat[]
}
