"""会员主数据接口。"""
from sqlalchemy.orm import Session

from app.services import member_service


def list_members(
    db: Session,
    search: str | None = None,
    store_code: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    return member_service.list_members(db, search, store_code, page, page_size)


def list_stores(db: Session) -> dict:
    return {"items": member_service.list_stores(db)}
