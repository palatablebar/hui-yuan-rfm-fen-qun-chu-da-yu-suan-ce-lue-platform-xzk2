import { defineStore } from 'pinia'
import { fetchOrderSummary } from '../api/order'
import type { OrderSummary } from '../types/order'

interface OrderState {
  summary: OrderSummary | null
  loading: boolean
  error: string
}

export const useOrderStore = defineStore('order', {
  state: (): OrderState => ({
    summary: null,
    loading: false,
    error: '',
  }),
  getters: {
    totals: (state) => state.summary?.totals ?? null,
    byStore: (state): Record<string, OrderSummary['stores'][number]> => {
      const map: Record<string, OrderSummary['stores'][number]> = {}
      for (const item of state.summary?.stores ?? []) map[item.store_code] = item
      return map
    },
  },
  actions: {
    async loadSummary() {
      this.loading = true
      this.error = ''
      try {
        this.summary = await fetchOrderSummary()
        return this.summary
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载订单事实失败'
        throw error
      } finally {
        this.loading = false
      }
    },
  },
})
