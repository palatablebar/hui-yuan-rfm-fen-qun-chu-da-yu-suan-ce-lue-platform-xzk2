from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class OrderFact(Base):
    """POS 订单事实（核心实体 2）；金额单位为元。"""

    __tablename__ = "order_facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    store_code: Mapped[str] = mapped_column(String(12))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    coupon_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    coupon_redeemed: Mapped[bool] = mapped_column(Boolean, default=False)
    coupon_discount: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member = relationship("Member", lazy="joined")
