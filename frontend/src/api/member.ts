import type { MemberRow, StoreOption } from '../types/member'
import type { Paginated } from '../types/api'
import { http } from './http'

export function fetchMembers(params: {
  search?: string
  store_code?: string
  page?: number
  page_size?: number
}): Promise<Paginated<MemberRow>> {
  const query = new URLSearchParams()
  if (params.search) query.set('search', params.search)
  if (params.store_code) query.set('store_code', params.store_code)
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 20))
  return http.get<Paginated<MemberRow>>(`/members?${query.toString()}`)
}

export function fetchStores(): Promise<{ items: StoreOption[] }> {
  return http.get<{ items: StoreOption[] }>('/members/stores')
}
