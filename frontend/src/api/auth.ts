import type { LoginResponse, User } from '../types/user'
import { http } from './http'

export function login(email: string, password: string): Promise<LoginResponse> {
  return http.post<LoginResponse>('/auth/login', { email, password })
}

export function fetchMe(): Promise<{ user: User }> {
  return http.get<{ user: User }>('/auth/me')
}
