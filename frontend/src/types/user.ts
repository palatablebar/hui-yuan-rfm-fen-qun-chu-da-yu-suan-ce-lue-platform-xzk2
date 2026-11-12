export type Role = 'admin' | 'analyst' | 'viewer'

export interface User {
  id: number
  email: string
  display_name: string
  role: Role
  role_label: string
  permissions: string[]
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in_hours: number
  user: User
}
