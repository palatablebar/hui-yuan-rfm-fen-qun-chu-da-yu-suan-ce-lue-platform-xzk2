"""分群批次接口。"""
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.middlewares.audit_logger import record
from app.models import User
from app.schemas.segment import RunCreateRequest
from app.services import segment_service


def create_run(db: Session, request: Request, user: User, payload: RunCreateRequest):
    run, replayed = segment_service.create_run(db, payload, user)
    record(
        request,
        "segment.run.replay" if replayed else "segment.run.create",
        "segment_run",
        run.id,
        after={
            "run_no": run.run_no,
            "k_requested": run.k_requested,
            "status": run.status,
            "as_of": run.as_of.isoformat(),
            "replayed": replayed,
            "is_current": run.is_current,
        },
    )
    body = {
        "run": segment_service.serialize_run(run, detail=False),
        "replayed": replayed,
    }
    # 幂等复用没有创建新资源，按 200 返回；真正新建才是 201
    if replayed:
        return JSONResponse(status_code=200, content=body)
    return body


def list_runs(db: Session, limit: int = 20) -> dict:
    return {"items": segment_service.list_runs(db, limit)}


def current_run(db: Session) -> dict:
    run = segment_service.get_current(db)
    if run is None:
        return {"run": None}
    return {"run": segment_service.serialize_run(run, detail=True)}


def get_run(db: Session, run_id: int) -> dict:
    run = segment_service.get_run(db, run_id)
    return {"run": segment_service.serialize_run(run, detail=True)}


def activate_run(db: Session, request: Request, run_id: int) -> dict:
    run = segment_service.activate_current_run(db, run_id)
    record(
        request,
        "segment.run.activate",
        "segment_run",
        run.id,
        after={"run_no": run.run_no, "is_current": True},
    )
    return {"run": segment_service.serialize_run(run, detail=True)}


def reconcile_run(db: Session, run_id: int) -> dict:
    return segment_service.get_reconciliation(db, run_id)


def list_run_members(
    db: Session,
    run_id: int,
    cluster_key: str | None,
    search: str | None,
    page: int,
    page_size: int,
) -> dict:
    return segment_service.get_run_members(db, run_id, cluster_key, search, page, page_size)
