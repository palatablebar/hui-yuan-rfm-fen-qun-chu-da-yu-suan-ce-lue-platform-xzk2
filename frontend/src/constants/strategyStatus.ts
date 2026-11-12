import type { StrategyStatus } from '../types/strategy'

// 与后端 backend/app/constants/strategy_status.py 同值镜像
export const STRATEGY_STATUS_META: Record<StrategyStatus, { label: string; tone: string }> = {
  draft: { label: '草稿', tone: 'muted' },
  published: { label: '已发布', tone: 'ok' },
  archived: { label: '已归档', tone: 'muted' },
}
