from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.constants.roles import ROLE_ADMIN, ROLE_ANALYST, SEGMENT_WRITE_ROLES
from app.controllers import segment_controller
from app.middlewares.auth import get_current_user, require_roles
from app.models import User
from app.schemas.segment import RunCreateRequest

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get("/runs")
def list_runs(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return segment_controller.list_runs(db, limit)


@router.post("/runs", status_code=201)
def create_run(
    payload: RunCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*sorted(SEGMENT_WRITE_ROLES))),
) -> dict:
    return segment_controller.create_run(db, request, user, payload)


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return segment_controller.get_run(db, run_id)


@router.get("/runs/{run_id}/members")
def list_run_members(
    run_id: int,
    cluster_key: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return segment_controller.list_run_members(db, run_id, cluster_key, search, page, page_size)
