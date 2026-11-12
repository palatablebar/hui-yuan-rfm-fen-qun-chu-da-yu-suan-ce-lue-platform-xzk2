import type { Role } from '../types/user'

// 与后端 backend/app/constants/roles.py 同值镜像（README §共享枚举）
export const ROLE_META: Record<Role, { label: string; hint: string }> = {
  admin: { label: '运营主管', hint: '分群参数 / 策略与预算 / 发布' },
  analyst: { label: '会员分析师', hint: '跑分群 / 看画像 / 调参 / 导出名单' },
  viewer: { label: '店长', hint: '只读分群结论与名单' },
}

export const ROLE_ORDER: Role[] = ['admin', 'analyst', 'viewer']
