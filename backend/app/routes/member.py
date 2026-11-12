from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import member_controller
from app.middlewares.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/members", tags=["members"])


@router.get("")
def list_members(
    search: str | None = None,
    store_code: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return member_controller.list_members(db, search, store_code, page, page_size)


@router.get("/stores")
def list_stores(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return member_controller.list_stores(db)
