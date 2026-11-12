"""审计日志查询。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.utils.formatting import to_iso


def list_logs(db: Session, page: int, page_size: int, action: str | None = None) -> dict:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "actor_email": row.actor_email,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "after": row.after_json,
                "ip": row.ip,
                "created_at": to_iso(row.created_at),
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
