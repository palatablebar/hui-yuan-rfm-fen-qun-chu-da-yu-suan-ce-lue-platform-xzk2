import type { SegmentStatus } from '../types/segment'

// 与后端 backend/app/constants/segment_status.py 同值镜像
export const SEGMENT_STATUS_META: Record<SegmentStatus, { label: string; tone: string }> = {
  queued: { label: '排队中', tone: 'muted' },
  running: { label: '计算中', tone: 'ochre' },
  completed: { label: '已完成', tone: 'ok' },
  failed: { label: '失败', tone: 'danger' },
}

export const TERMINAL_STATUSES: SegmentStatus[] = ['completed', 'failed']
