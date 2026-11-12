// 与后端 backend/app/constants/cluster_kinds.py 同值镜像（仅用于展示色/文案）
export interface ClusterKindMeta {
  label: string
  short: string
  color: string
}

export const CLUSTER_KIND_META: Record<string, ClusterKindMeta> = {
  HIGH_VALUE_DORMANT: { label: '高价值沉睡', short: '沉睡', color: 'var(--rust)' },
  CORE_ACTIVE: { label: '核心活跃', short: '核心', color: 'var(--ochre)' },
  NEW_NURTURE: { label: '新客培育', short: '新客', color: 'var(--moss)' },
  PRICE_SENSITIVE: { label: '价格敏感', short: '敏感', color: 'var(--sand-4)' },
  LOW_FREQ_CHURN: { label: '低频流失', short: '流失', color: 'var(--slate)' },
  STABLE_POTENTIAL: { label: '稳定潜力', short: '稳定', color: 'var(--sand-3)' },
}

export function clusterColor(kind: string | undefined): string {
  return (kind && CLUSTER_KIND_META[kind]?.color) || 'var(--sand-3)'
}
