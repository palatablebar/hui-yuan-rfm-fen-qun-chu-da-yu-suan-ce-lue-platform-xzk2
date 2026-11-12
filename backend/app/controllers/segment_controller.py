"""分群批次接口。"""
from fastapi import Request
from sqlalchemy.orm import Session

from app.middlewares.audit_logger import record
from app.models import User
from app.schemas.segment import RunCreateRequest
from app.services import segment_service


def create_run(db: Session, request: Request, user: User, payload: RunCreateRequest) -> dict:
    run = segment_service.create_run(db, payload, user)
    record(
        request,
        "segment.run.create",
        "segment_run",
        run.id,
        after={
            "run_no": run.run_no,
            "k_requested": run.k_requested,
            "status": run.status,
            "as_of": run.as_of.isoformat(),
        },
    )
    return {"run": segment_service.serialize_run(run, detail=False)}


def list_runs(db: Session, limit: int = 20) -> dict:
    return {"items": segment_service.list_runs(db, limit)}


def get_run(db: Session, run_id: int) -> dict:
    run = segment_service.get_run(db, run_id)
    return {"run": segment_service.serialize_run(run, detail=True)}


def list_run_members(
    db: Session,
    run_id: int,
    cluster_key: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    return segment_service.get_run_members(db, run_id, cluster_key, search, page, page_size)
