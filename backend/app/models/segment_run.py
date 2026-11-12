from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class SegmentRun(Base):
    """分群批次与簇结果（核心实体 3）。

    `result` 是算法完整快照（簇画像 / 每人分数 / 直方图 / 散点），
    保证「同一批数据 + 同一 random_state → 同一结果」可被审计复算。

    版本化（订单补录场景）：
    - 历史批次全部保留，仅 `is_current=True` 的批次是当前版本，同一时刻至多一条；
    - `input_fingerprint` 覆盖 as-of / k / 会员与订单事实内容，重复补录命中同一指纹，
      创建接口直接复用旧批次，不新增名单、不触发预算占用；
    - 新批次整批校验通过后才在一个事务内切换 `is_current`，失败批次保留报告
      （`validation_report`）且不影响原当前版本。
    """

    __tablename__ = "segment_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16), index=True, default="queued")
    k_requested: Mapped[str] = mapped_column(String(8), default="auto")
    as_of: Mapped[date] = mapped_column(Date)
    random_state: Mapped[int] = mapped_column(Integer, default=5741)
    selected_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    silhouette: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    inertia: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    member_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    validation_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
