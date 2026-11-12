export interface ApiErrorPayload {
  code: string
  message: string
  request_id?: string
  detail?: unknown
}

export class ApiError extends Error {
  status: number
  code: string
  detail?: unknown

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message || '请求失败')
    this.status = status
    this.code = payload.code || `HTTP-${status}`
    this.detail = payload.detail
  }
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}
