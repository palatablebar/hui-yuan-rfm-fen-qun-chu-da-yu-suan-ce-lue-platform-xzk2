import { defineStore } from 'pinia'
import { fetchMe, login as apiLogin } from '../api/auth'
import type { Role, User } from '../types/user'
import { clearToken, getToken, setToken } from '../utils/request'

interface AuthState {
  token: string
  user: User | null
  loading: boolean
  error: string
  restored: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: getToken(),
    user: null,
    loading: false,
    error: '',
    restored: false,
  }),
  getters: {
    isAuthenticated: (state): boolean => Boolean(state.token),
    role: (state): Role => (state.user?.role ?? 'viewer') as Role,
    isAdmin: (state): boolean => state.user?.role === 'admin',
    canRunSegment: (state): boolean =>
      state.user?.role === 'admin' || state.user?.role === 'analyst',
    canWriteStrategy: (state): boolean => state.user?.role === 'admin',
    canExport: (state): boolean =>
      state.user?.role === 'admin' || state.user?.role === 'analyst',
    displayName: (state): string => state.user?.display_name ?? '',
    roleLabel: (state): string => state.user?.role_label ?? '',
  },
  actions: {
    async login(email: string, password: string) {
      this.loading = true
      this.error = ''
      try {
        const result = await apiLogin(email, password)
        this.token = result.access_token
        this.user = result.user
        setToken(result.access_token)
        this.restored = true
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async restore() {
      if (!this.token) return
      try {
        const result = await fetchMe()
        this.user = result.user
      } catch {
        this.logout()
      } finally {
        this.restored = true
      }
    },
    logout() {
      this.token = ''
      this.user = null
      this.error = ''
      clearToken()
    },
  },
})
