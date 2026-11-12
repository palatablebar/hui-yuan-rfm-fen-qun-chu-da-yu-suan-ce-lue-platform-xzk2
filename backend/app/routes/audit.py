from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.constants.roles import ADMIN_ONLY
from app.controllers import audit_controller
from app.middlewares.auth import require_roles
from app.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*sorted(ADMIN_ONLY))),
) -> dict:
    return audit_controller.list_logs(db, page, page_size, action)
