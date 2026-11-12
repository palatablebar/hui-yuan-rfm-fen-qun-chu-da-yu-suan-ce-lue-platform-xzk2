import { defineStore } from 'pinia'
import { fetchMembers, fetchStores } from '../api/member'
import type { Paginated } from '../types/api'
import type { MemberRow, StoreOption } from '../types/member'

interface MemberState {
  stores: StoreOption[]
  members: Paginated<MemberRow> | null
  loading: boolean
  error: string
}

export const useMemberStore = defineStore('member', {
  state: (): MemberState => ({
    stores: [],
    members: null,
    loading: false,
    error: '',
  }),
  actions: {
    async loadStores() {
      try {
        const result = await fetchStores()
        this.stores = result.items
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载门店失败'
      }
    },
    async loadMembers(params: { search?: string; store_code?: string; page?: number; page_size?: number }) {
      this.loading = true
      this.error = ''
      try {
        this.members = await fetchMembers(params)
        return this.members
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载会员主数据失败'
        throw error
      } finally {
        this.loading = false
      }
    },
  },
})
