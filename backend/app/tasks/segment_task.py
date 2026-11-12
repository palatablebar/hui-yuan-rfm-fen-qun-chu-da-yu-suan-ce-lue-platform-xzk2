"""Celery 任务：在 worker 中执行一次分群计算。"""
from app.config.celery_app import celery_app
from app.config.database import SessionLocal
from app.models import SegmentRun
from app.services import segment_service
from app.utils.logger import log_event


@celery_app.task(name="segment.run", bind=True, max_retries=0)
def run_segment_task(self, run_id: int) -> dict:
    db = SessionLocal()
    try:
        run = db.get(SegmentRun, int(run_id))
        if run is None:
            log_event("SEGMENT_TASK_MISSING", run_id=run_id)
            return {"run_id": run_id, "status": "missing"}
        if run.status in ("completed", "failed"):
            return {"run_id": run_id, "status": run.status}
        segment_service.execute_run_sync(db, run)
        return {
            "run_id": run_id,
            "status": run.status,
            "selected_k": run.selected_k,
            "silhouette": float(run.silhouette) if run.silhouette is not None else None,
        }
    finally:
        db.close()
