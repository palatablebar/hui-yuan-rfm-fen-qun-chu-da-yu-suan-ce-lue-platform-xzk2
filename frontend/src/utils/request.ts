import { ApiError, type ApiErrorPayload } from '../types/api'

export const TOKEN_KEY = 'rfmseg_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload = { code: `HTTP-${response.status}`, message: response.statusText || '请求失败' }
  try {
    const data = (await response.json()) as { error?: ApiErrorPayload }
    if (data?.error) payload = data.error
  } catch {
    /* 非 JSON 响应保留状态码兜底 */
  }
  return new ApiError(response.status, payload)
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers ?? {}),
  }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const response = await fetch(`/api${path}`, {
    method: options.method ?? 'GET',
    headers,
    body:
      options.body === undefined
        ? undefined
        : options.body instanceof FormData
          ? (options.body as FormData)
          : JSON.stringify(options.body),
  })
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function downloadFile(path: string, fallbackName: string): Promise<string> {
  const token = getToken()
  const response = await fetch(`/api${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw await parseError(response)
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const match = /filename\*=UTF-8''([^;]+)/.exec(disposition)
  const name = match ? decodeURIComponent(match[1]) : fallbackName
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
  return name
}
