from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Member(Base):
    """会员主数据（`rbac`/seed 之外的核心实体 1）。"""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_no: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    phone: Mapped[str] = mapped_column(String(24))
    store_code: Mapped[str] = mapped_column(String(12), index=True)
    store_name: Mapped[str] = mapped_column(String(60))
    joined_at: Mapped[date] = mapped_column(Date)
    consent: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
