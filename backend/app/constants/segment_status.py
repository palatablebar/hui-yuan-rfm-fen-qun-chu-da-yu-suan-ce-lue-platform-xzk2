"""共享枚举：分群批次状态。前端 src/constants/segmentStatus.ts 同值镜像。"""

SEGMENT_STATUS = {
    "queued": "排队中",
    "running": "计算中",
    "completed": "已完成",
    "failed": "失败",
}
SEGMENT_STATUS_SET = set(SEGMENT_STATUS)
TERMINAL_STATUSES = {"completed", "failed"}
