import type { OrderSummary } from '../types/order'
import { http } from './http'

export function fetchOrderSummary(): Promise<OrderSummary> {
  return http.get<OrderSummary>('/orders/summary')
}
