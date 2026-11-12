"""审计日志（admin 只读）。"""
from sqlalchemy.orm import Session

from app.services import audit_service


def list_logs(db: Session, page: int = 1, page_size: int = 20, action: str | None = None) -> dict:
    return audit_service.list_logs(db, page, page_size, action)
