"""策略与名单导出接口。"""
from fastapi import Request
from sqlalchemy.orm import Session

from app.middlewares.audit_logger import record
from app.models import User
from app.schemas.strategy import ExportCreateRequest, PublishRequest, StrategyCreateRequest
from app.services import strategy_service


def create_strategy(db: Session, request: Request, user: User, payload: StrategyCreateRequest) -> dict:
    strategy = strategy_service.create_strategy(db, payload, user)
    record(
        request,
        "strategy.create",
        "strategy",
        strategy.id,
        after={
            "strategy_no": strategy.strategy_no,
            "run_id": strategy.run_id,
            "total_budget": float(strategy.total_budget),
            "tiers_used": strategy.tiers_used,
        },
    )
    return {"strategy": strategy_service.serialize_strategy(db, strategy)}


def list_strategies(db: Session, run_id: int | None = None) -> dict:
    return {"items": strategy_service.list_strategies(db, run_id)}


def get_strategy(db: Session, strategy_id: int) -> dict:
    strategy = strategy_service.get_strategy(db, strategy_id)
    return {"strategy": strategy_service.serialize_strategy(db, strategy)}


def publish_strategy(db: Session, request: Request, strategy_id: int, payload: PublishRequest) -> dict:
    strategy = strategy_service.get_strategy(db, strategy_id)
    strategy = strategy_service.publish_strategy(db, strategy, payload.note)
    record(request, "strategy.publish", "strategy", strategy.id, after={"status": strategy.status})
    return {"strategy": strategy_service.serialize_strategy(db, strategy)}


def create_export(
    db: Session,
    request: Request,
    user: User,
    strategy_id: int,
    payload: ExportCreateRequest,
) -> dict:
    strategy = strategy_service.get_strategy(db, strategy_id)
    result = strategy_service.record_export(db, strategy, payload, user)
    record(
        request,
        "strategy.export",
        "strategy",
        strategy.id,
        after={
            "export_id": result["entry"]["id"],
            "cluster_key": result["entry"]["cluster_key"],
            "row_count": result["entry"]["row_count"],
        },
    )
    return result


def preview_export(db: Session, strategy_id: int, cluster_key: str) -> dict:
    strategy = strategy_service.get_strategy(db, strategy_id)
    return strategy_service.preview_export(db, strategy, cluster_key)
