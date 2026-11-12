"""分群批次：创建、执行、查询、名单读取。

- 创建：落库 queued → 投递 Celery；broker 不可用时同步回退（保证主流程可用）。
- 执行：读会员/订单事实 → rfm_engine 真算 → 结果快照写 JSONB。
- 查询：批次详情 / 簇成员分页 / 全量导出数据。
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.constants.error_codes import AppError, ErrorCode
from app.constants.rfm import REFERENCE_DATE, RANDOM_STATE
from app.models import Member, OrderFact, SegmentRun, User
from app.services import batch_versioning, rfm_engine
from app.utils.formatting import to_iso
from app.utils.logger import log_event
from app.utils.pagination import page_params, paginated


def _next_run_no(db: Session, as_of: date) -> str:
    prefix = f"SEG-{as_of:%Y%m%d}"
    count = (
        db.scalar(
            select(func.count())
            .select_from(SegmentRun)
            .where(SegmentRun.run_no.like(f"{prefix}-%"))
        )
        or 0
    )
    return f"{prefix}-{count + 1:03d}"


def serialize_run_summary(run: SegmentRun) -> dict:
    cluster_count = 0
    if run.result and isinstance(run.result, dict):
        cluster_count = len(run.result.get("clusters") or [])
    report = run.validation_report if isinstance(run.validation_report, dict) else None
    return {
        "id": run.id,
        "run_no": run.run_no,
        "name": run.name,
        "status": run.status,
        "k_requested": run.k_requested,
        "as_of": run.as_of.isoformat(),
        "random_state": run.random_state,
        "selected_k": run.selected_k,
        "silhouette": float(run.silhouette) if run.silhouette is not None else None,
        "member_count": run.member_count,
        "cluster_count": cluster_count,
        "duration_ms": run.duration_ms,
        "error_message": run.error_message,
        "is_current": run.is_current,
        "current_since": to_iso(run.current_since),
        "input_fingerprint": run.input_fingerprint,
        "validation_ok": report.get("ok") if report else None,
        "created_at": to_iso(run.created_at),
        "completed_at": to_iso(run.completed_at),
    }


def serialize_run(run: SegmentRun, detail: bool = False) -> dict:
    payload = serialize_run_summary(run)
    if detail and run.result:
        result = run.result
        payload.update(
            {
                "clusters": result.get("clusters", []),
                "silhouette_curve": result.get("silhouette_curve", []),
                "histograms": result.get("histograms", {}),
                "scatter": result.get("scatter", []),
                "gmv_total": result.get("gmv_total"),
                "assignments_count": len(result.get("assignments") or []),
                "scoring_note": result.get("scoring_note"),
                "validation_report": run.validation_report,
                "k_min": 3,
                "k_max": 8,
            }
        )
    elif detail:
        payload["validation_report"] = run.validation_report
    return payload


def create_run(db: Session, payload, user: User, run_no: str | None = None) -> tuple[SegmentRun, bool]:
    """创建分群批次，返回 ``(run, replayed)``。

    幂等：相同 as-of / k / 会员与订单事实内容（input_fingerprint）已存在有效批次时，
    直接复用旧批次，不新增批次、名单与触达记录，也不触发任何预算占用。
    """
    raw_k = payload.k
    if raw_k in (None, "", "auto"):
        k_value = "auto"
    else:
        try:
            k_int = int(raw_k)
        except (TypeError, ValueError) as exc:
            raise AppError(ErrorCode.VALIDATION, "k 只能是 auto 或 2-8 的整数", 422) from exc
        if not (2 <= k_int <= 8):
            raise AppError(ErrorCode.VALIDATION, "k 必须在 2-8 之间", 422)
        k_value = str(k_int)

    as_of = payload.as_of or REFERENCE_DATE
    fingerprint = batch_versioning.input_fingerprint(db, as_of, k_value, RANDOM_STATE)

    # 同一补录重复运行：命中指纹直接复用，不计配额、不落新批次
    existing = batch_versioning.find_replayable_run(db, fingerprint)
    if existing is not None:
        log_event(
            "SEGMENT_REPLAY_DEDUP",
            run_id=existing.id,
            run_no=existing.run_no,
            fingerprint=fingerprint[:12],
        )
        return existing, True

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = (
        db.scalar(
            select(func.count())
            .select_from(SegmentRun)
            .where(SegmentRun.created_by == user.id, SegmentRun.created_at >= since)
        )
        or 0
    )
    if recent >= settings.RUN_DAILY_QUOTA:
        raise AppError(
            ErrorCode.QUOTA_EXCEEDED,
            f"24 小时内最多创建 {settings.RUN_DAILY_QUOTA} 个分群批次",
            429,
        )

    name = (payload.name or "").strip() or f"{as_of.isoformat()} 会员 RFM 分群"
    run = SegmentRun(
        run_no=run_no or _next_run_no(db, as_of),
        name=name,
        status="queued",
        k_requested=k_value,
        as_of=as_of,
        random_state=RANDOM_STATE,
        input_fingerprint=fingerprint,
        created_by=user.id,
    )
    db.add(run)
    try:
        db.commit()
    except Exception as exc:  # 并发下同一指纹的唯一索引冲突 → 回退为幂等复用
        db.rollback()
        existing = batch_versioning.find_replayable_run(db, fingerprint)
        if existing is not None:
            log_event(
                "SEGMENT_REPLAY_RACE",
                run_id=existing.id,
                run_no=existing.run_no,
                fingerprint=fingerprint[:12],
            )
            return existing, True
        raise AppError(
            ErrorCode.QUOTA_EXCEEDED,
            "分群批次创建冲突，请稍后重试",
            409,
            {"reason": f"{type(exc).__name__}: {exc}"},
        ) from exc
    db.refresh(run)

    try:
        from app.tasks.segment_task import run_segment_task

        run_segment_task.delay(run.id)
        log_event("SEGMENT_DISPATCHED", run_id=run.id, run_no=run.run_no)
    except Exception as exc:  # broker 不可用：同步回退，主流程不中断
        log_event("SEGMENT_DISPATCH_FALLBACK", run_id=run.id, reason=f"{type(exc).__name__}: {exc}")
        execute_run_sync(db, run)
    db.refresh(run)
    return run, False


def execute_run_sync(db: Session, run: SegmentRun) -> SegmentRun:
    if run.status == "completed":
        return run
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    db.commit()
    started = time.perf_counter()
    try:
        members = db.scalars(select(Member).order_by(Member.id)).all()
        orders = db.scalars(select(OrderFact).order_by(OrderFact.id)).all()
        member_rows = [
            {
                "member_id": member.id,
                "member_no": member.member_no,
                "name": member.name,
                "store_code": member.store_code,
                "store_name": member.store_name,
                "consent": member.consent,
                "joined_at": member.joined_at,
            }
            for member in members
        ]
        order_rows = [
            {
                "member_id": order.member_id,
                "amount": float(order.amount),
                "ordered_at": order.ordered_at,
                "coupon_issued": order.coupon_issued,
                "coupon_redeemed": order.coupon_redeemed,
            }
            for order in orders
        ]
        k_arg = "auto" if run.k_requested == "auto" else int(run.k_requested)
        result = rfm_engine.run_segmentation(
            member_rows,
            order_rows,
            as_of=run.as_of,
            k=k_arg,
            random_state=run.random_state,
        )
        run.result = result
        run.status = "completed"
        run.selected_k = result["selected_k"]
        run.silhouette = result["silhouette"]
        run.inertia = result["inertia"]
        run.member_count = result["member_count"]
        run.error_message = None

        # 整批校验：会员 / 订单 / 簇人数三方对账，通过后才允许成为当前版本
        report = batch_versioning.validate_run_result(db, run)
        run.validation_report = report
        if report["ok"]:
            # 单事务切换：旧批次保留为历史版本，新批次成为当前版本
            batch_versioning.activate_run(db, run)
            log_event(
                "SEGMENT_ACTIVATED",
                run_id=run.id,
                run_no=run.run_no,
                fingerprint=(run.input_fingerprint or "")[:12],
            )
        else:
            # 校验失败：批次保留、报告留存，原当前版本（若有）保持不变
            run.is_current = False
            run.current_since = None
            run.error_message = "整批校验未通过，未切换当前版本"
            log_event("SEGMENT_BATCH_INVALID", run_id=run.id, run_no=run.run_no)
        log_event(
            "SEGMENT_COMPLETED",
            run_id=run.id,
            run_no=run.run_no,
            k=result["selected_k"],
            silhouette=result["silhouette"],
            members=result["member_count"],
            validation_ok=report["ok"],
        )
    except rfm_engine.SegmentationError as exc:
        run.status = "failed"
        run.error_message = exc.message
        log_event("SEGMENT_FAILED", run_id=run.id, reason=exc.message)
    except Exception as exc:  # pragma: no cover - 兜底
        run.status = "failed"
        run.error_message = f"{type(exc).__name__}: {exc}"
        log_event("SEGMENT_FAILED", run_id=run.id, reason=run.error_message)
    finally:
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
    return run


def activate_current_run(db: Session, run_id: int) -> SegmentRun:
    """手动把一个已通过校验的历史批次设为当前版本。"""
    run = get_run(db, run_id)
    activated = batch_versioning.activate_run(db, run)
    log_event("SEGMENT_MANUAL_ACTIVATE", run_id=activated.id, run_no=activated.run_no)
    return activated


def get_current(db: Session) -> SegmentRun | None:
    return batch_versioning.get_current_run(db)


def get_reconciliation(db: Session, run_id: int) -> dict:
    run = get_run(db, run_id)
    return batch_versioning.reconcile_run(db, run)


def list_runs(db: Session, limit: int = 20) -> list[dict]:
    rows = db.scalars(
        select(SegmentRun).order_by(SegmentRun.id.desc()).limit(max(1, min(limit, 50)))
    ).all()
    return [serialize_run_summary(row) for row in rows]


def get_run(db: Session, run_id: int) -> SegmentRun:
    run = db.get(SegmentRun, run_id)
    if run is None:
        raise AppError(ErrorCode.NOT_FOUND, "分群批次不存在", 404)
    return run


def _enriched_cluster_members(db: Session, run: SegmentRun, cluster_key: str) -> list[dict]:
    if run.status != "completed" or not run.result:
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成", 409)
    assignments = [
        item
        for item in (run.result.get("assignments") or [])
        if item.get("cluster_key") == cluster_key
    ]
    if not assignments:
        raise AppError(ErrorCode.NOT_FOUND, f"簇 {cluster_key} 不存在", 404)
    member_ids = [int(item["member_id"]) for item in assignments]
    members = db.scalars(select(Member).where(Member.id.in_(member_ids))).all()
    member_map = {member.id: member for member in members}
    rows = []
    for item in assignments:
        member = member_map.get(int(item["member_id"]))
        if member is None:
            continue
        rows.append(
            {
                "member_id": member.id,
                "member_no": member.member_no,
                "name": member.name,
                "phone": member.phone,
                "store_code": member.store_code,
                "store_name": member.store_name,
                "consent": member.consent,
                "recency_days": item["recency_days"],
                "frequency": item["frequency"],
                "monetary": item["monetary"],
                "r_score": item["r_score"],
                "f_score": item["f_score"],
                "m_score": item["m_score"],
                "cluster_key": item["cluster_key"],
            }
        )
    rows.sort(key=lambda row: (-row["monetary"], row["member_no"]))
    return rows


def get_run_members(
    db: Session,
    run_id: int,
    cluster_key: str | None,
    search: str | None,
    page: int | None,
    page_size: int | None,
) -> dict:
    run = get_run(db, run_id)
    if run.status != "completed" or not run.result:
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成", 409)
    current, size = page_params(page, page_size)
    assignments = run.result.get("assignments") or []
    keys = [item["cluster_key"] for item in assignments]
    selected_key = cluster_key or (run.result.get("clusters") or [{}])[0].get("cluster_key")
    if cluster_key and cluster_key not in keys:
        raise AppError(ErrorCode.NOT_FOUND, f"簇 {cluster_key} 不存在", 404)
    rows = _enriched_cluster_members(db, run, selected_key)
    if search:
        needle = search.strip().lower()
        rows = [
            row
            for row in rows
            if needle in row["member_no"].lower()
            or needle in row["name"].lower()
            or needle in row["phone"].lower()
        ]
    total = len(rows)
    start = (current - 1) * size
    return paginated(rows[start : start + size], total, current, size)


def get_cluster_members_all(db: Session, run: SegmentRun, cluster_key: str) -> list[dict]:
    return _enriched_cluster_members(db, run, cluster_key)


def cluster_by_key(run: SegmentRun, cluster_key: str) -> dict | None:
    for cluster in (run.result or {}).get("clusters", []):
        if cluster.get("cluster_key") == cluster_key:
            return cluster
    return None
