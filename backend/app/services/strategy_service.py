"""策略与券预算：分配、发布、名单导出 / 触达记录。"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import AppError, ErrorCode
from app.models import SegmentRun, Strategy, User
from app.services import budget_engine, segment_service
from app.utils.formatting import to_iso


def _next_strategy_no(db: Session) -> str:
    prefix = f"STR-{date.today():%Y%m%d}"
    count = (
        db.scalar(
            select(func.count())
            .select_from(Strategy)
            .where(Strategy.strategy_no.like(f"{prefix}-%"))
        )
        or 0
    )
    return f"{prefix}-{count + 1:02d}"


def create_strategy(db: Session, payload, user: User) -> Strategy:
    run = segment_service.get_run(db, payload.run_id)
    if run.status != "completed" or not run.result:
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成，无法生成策略", 409)
    try:
        allocation = budget_engine.allocate_budget(run.result.get("clusters") or [], payload.total_budget)
    except budget_engine.BudgetError as exc:
        raise AppError(exc.code, exc.message, 422, exc.detail) from exc

    name = (payload.name or "").strip() or f"{run.run_no} · 触达预算方案"
    strategy = Strategy(
        strategy_no=_next_strategy_no(db),
        name=name,
        status="draft",
        run_id=run.id,
        total_budget=allocation["totals"]["budget"],
        allocations=allocation["allocations"],
        totals={
            **allocation["totals"],
            "tier_policy": allocation["tier_policy"],
            "step": allocation["step"],
        },
        tiers_used=allocation["tiers_used"],
        touch_log=[],
        created_by=user.id,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def serialize_strategy(db: Session, strategy: Strategy) -> dict:
    run = db.get(SegmentRun, strategy.run_id)
    entries = strategy.touch_log or []
    return {
        "id": strategy.id,
        "strategy_no": strategy.strategy_no,
        "name": strategy.name,
        "status": strategy.status,
        "run_id": strategy.run_id,
        "run_no": run.run_no if run else None,
        "run_as_of": run.as_of.isoformat() if run else None,
        "selected_k": run.selected_k if run else None,
        "silhouette": float(run.silhouette) if run and run.silhouette is not None else None,
        "total_budget": float(strategy.total_budget),
        "allocations": strategy.allocations or [],
        "totals": strategy.totals or {},
        "tiers_used": strategy.tiers_used or [],
        "touch_log": entries,
        "export_count": len([entry for entry in entries if entry.get("kind") == "export"]),
        "created_at": to_iso(strategy.created_at),
        "updated_at": to_iso(strategy.updated_at),
        "published_at": to_iso(strategy.published_at),
    }


def list_strategies(db: Session, run_id: int | None = None) -> list[dict]:
    stmt = select(Strategy).order_by(Strategy.id.desc()).limit(30)
    if run_id:
        stmt = stmt.where(Strategy.run_id == run_id)
    rows = db.scalars(stmt).all()
    return [serialize_strategy(db, row) for row in rows]


def get_strategy(db: Session, strategy_id: int) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise AppError(ErrorCode.NOT_FOUND, "策略不存在", 404)
    return strategy


def publish_strategy(db: Session, strategy: Strategy, note: str | None) -> Strategy:
    if strategy.status == "published":
        return strategy
    strategy.status = "published"
    strategy.published_at = datetime.now(timezone.utc)
    log = list(strategy.touch_log or [])
    log.append(
        {
            "id": f"PUB-{len(log) + 1:03d}",
            "kind": "publish",
            "channel": "系统",
            "note": note or "策略发布到门店券核销系统",
            "row_count": 0,
            "created_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    strategy.touch_log = log
    db.commit()
    db.refresh(strategy)
    return strategy


def _cluster_or_404(run: SegmentRun, cluster_key: str) -> dict:
    cluster = segment_service.cluster_by_key(run, cluster_key)
    if cluster is None:
        raise AppError(ErrorCode.NOT_FOUND, f"簇 {cluster_key} 不存在", 404)
    return cluster


def preview_export(db: Session, strategy: Strategy, cluster_key: str) -> dict:
    run = db.get(SegmentRun, strategy.run_id)
    if run is None or run.status != "completed":
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成", 409)
    cluster = _cluster_or_404(run, cluster_key)
    rows = segment_service.get_cluster_members_all(db, run, cluster_key)
    allocation = next(
        (item for item in (strategy.allocations or []) if item.get("cluster_key") == cluster_key),
        None,
    )
    return {
        "cluster_key": cluster_key,
        "cluster_label": cluster.get("label"),
        "row_count": len(rows),
        "reachable_count": cluster.get("reachable_count"),
        "coupon_face": allocation.get("coupon_face") if allocation else None,
        "budget": allocation.get("budget") if allocation else None,
    }


def record_export(db: Session, strategy: Strategy, payload, user: User) -> dict:
    run = db.get(SegmentRun, strategy.run_id)
    if run is None or run.status != "completed":
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成", 409)
    cluster = _cluster_or_404(run, payload.cluster_key)
    rows = segment_service.get_cluster_members_all(db, run, payload.cluster_key)
    entries = list(strategy.touch_log or [])
    sequence = len([entry for entry in entries if str(entry.get("id", "")).startswith("EXP-")]) + 1
    entry = {
        "id": f"EXP-{sequence:04d}",
        "kind": "export",
        "cluster_key": payload.cluster_key,
        "cluster_label": cluster.get("label"),
        "channel": payload.channel,
        "note": payload.note or "门店券核销系统名单",
        "row_count": len(rows),
        "created_by": user.email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    strategy.touch_log = entries + [entry]
    db.commit()
    db.refresh(strategy)
    return {
        "entry": entry,
        "download_url": f"/api/strategies/{strategy.id}/exports/{entry['id']}/download",
    }


def _find_export(strategy: Strategy, export_id: str) -> dict:
    for entry in strategy.touch_log or []:
        if entry.get("id") == export_id and entry.get("kind") == "export":
            return entry
    raise AppError(ErrorCode.NOT_FOUND, f"导出记录 {export_id} 不存在", 404)


def build_export_csv(db: Session, strategy: Strategy, export_id: str) -> tuple[str, str]:
    run = db.get(SegmentRun, strategy.run_id)
    if run is None or run.status != "completed":
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成", 409)
    entry = _find_export(strategy, export_id)
    rows = segment_service.get_cluster_members_all(db, run, entry["cluster_key"])
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "会员编号",
            "姓名",
            "手机",
            "门店",
            "距今天数(R)",
            "订单数(F)",
            "累计消费(M,元)",
            "R分",
            "F分",
            "M分",
            "所属簇",
            "簇类型",
            "券面额建议(元)",
            "渠道",
        ]
    )
    allocation = next(
        (item for item in (strategy.allocations or []) if item.get("cluster_key") == entry["cluster_key"]),
        {},
    )
    for row in rows:
        writer.writerow(
            [
                row["member_no"],
                row["name"],
                row["phone"],
                row["store_name"],
                row["recency_days"],
                row["frequency"],
                f"{row['monetary']:.2f}",
                row["r_score"],
                row["f_score"],
                row["m_score"],
                entry["cluster_key"],
                entry.get("cluster_label"),
                allocation.get("coupon_face", ""),
                entry.get("channel", ""),
            ]
        )
    filename = f"{strategy.strategy_no}_{entry['cluster_key']}_名单_{len(rows)}人.csv"
    return "\ufeff" + buffer.getvalue(), filename
