"""订单事实接口。"""
from sqlalchemy.orm import Session

from app.services import order_service


def summary(db: Session) -> dict:
    return order_service.order_summary(db)
