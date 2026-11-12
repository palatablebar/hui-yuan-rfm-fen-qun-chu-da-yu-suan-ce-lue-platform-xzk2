"""数值/时间格式化小工具（后端统一格式化，前端只展示）。"""
from datetime import datetime, timezone


def to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def money(value: float | None) -> float:
    return round(float(value or 0.0), 2)


def ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)
