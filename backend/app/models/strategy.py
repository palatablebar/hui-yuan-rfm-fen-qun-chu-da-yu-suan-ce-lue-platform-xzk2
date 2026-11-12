from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Strategy(Base):
    """触达策略与券预算（核心实体 4）。

    `allocations` 保存预算分配结果，`touch_log` 保存名单导出/触达记录
    （同一个业务对象下的两类记录，页面「名单导出与触达记录」消费）。
    """

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(90))
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("segment_runs.id"), index=True)
    total_budget: Mapped[float] = mapped_column(Numeric(10, 2))
    allocations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    totals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tiers_used: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    touch_log: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
