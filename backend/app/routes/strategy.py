from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.constants.roles import EXPORT_ROLES, STRATEGY_WRITE_ROLES
from app.controllers import strategy_controller
from app.middlewares.auth import get_current_user, require_roles
from app.models import User
from app.schemas.strategy import ExportCreateRequest, PublishRequest, StrategyCreateRequest
from app.services import strategy_service

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("")
def list_strategies(
    run_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return strategy_controller.list_strategies(db, run_id)


@router.post("", status_code=201)
def create_strategy(
    payload: StrategyCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*sorted(STRATEGY_WRITE_ROLES))),
) -> dict:
    return strategy_controller.create_strategy(db, request, user, payload)


@router.get("/{strategy_id}")
def get_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return strategy_controller.get_strategy(db, strategy_id)


@router.post("/{strategy_id}/publish")
def publish_strategy(
    strategy_id: int,
    payload: PublishRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*sorted(STRATEGY_WRITE_ROLES))),
) -> dict:
    return strategy_controller.publish_strategy(db, request, strategy_id, payload)


@router.get("/{strategy_id}/exports/preview")
def preview_export(
    strategy_id: int,
    cluster_key: str = Query(min_length=2, max_length=8),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return strategy_controller.preview_export(db, strategy_id, cluster_key)


@router.post("/{strategy_id}/exports", status_code=201)
def create_export(
    strategy_id: int,
    payload: ExportCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*sorted(EXPORT_ROLES))),
) -> dict:
    return strategy_controller.create_export(db, request, user, strategy_id, payload)


@router.get("/{strategy_id}/exports/{export_id}/download")
def download_export(
    strategy_id: int,
    export_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Response:
    strategy = strategy_service.get_strategy(db, strategy_id)
    content, filename = strategy_service.build_export_csv(db, strategy, export_id)
    headers = {
        "Content-Disposition": f"attachment; filename=\"export.csv\"; filename*=UTF-8''{quote(filename)}",
        "X-Row-Count": str(content.count("\n") - 1),
    }
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=headers)
