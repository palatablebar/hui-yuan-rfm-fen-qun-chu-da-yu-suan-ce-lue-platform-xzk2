"""分群批次版本化：输入指纹、整批校验、当前版本切换、三方对账。

订单补录后同一统计日重跑分群的核心约束都在这里实现：

- :func:`input_fingerprint` 覆盖 as-of / k / 会员与订单事实的完整内容，
  「重复运行同一补录」会命中同一指纹 → 创建接口复用旧批次，不新增名单与触达、
  不重复占用预算；补录真实改变数据时指纹变化，才产生新批次。
- :func:`validate_run_result` 做整批校验（会员覆盖、订单归属、簇人数加总、
  可触达人数），任一不过即判失败，失败批次保留报告但不会被设为当前版本。
- :func:`activate_run` 在单个事务内把当前版本指针从旧批次切到新批次；
  切换失败（如批次未通过校验）时原当前版本保持不变。
- :func:`reconcile_run` 输出会员 / 订单 / 簇人数三方对账，供页面核对是否对得上。
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.constants.error_codes import AppError, ErrorCode
from app.models import Member, OrderFact, SegmentRun

FINGERPRINT_VERSION = "v1"


# ---------------------------------------------------------------------------
# 输入指纹：同一批数据 + 同一 as-of / k → 同一指纹
# ---------------------------------------------------------------------------

def _hash(parts: list[str]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="replace"))
        digest.update(b"\x1f")
    return digest.hexdigest()


def input_fingerprint(
    db: Session,
    as_of: date,
    k_value: str,
    random_state: int,
) -> str:
    """对分群输入做内容指纹。

    会员侧取自然键排序 + 授权标记；订单侧取自然键、归属会员、金额、下单时间、
    发券/核销标记。任一条补录、删除或改值都会改变指纹，而重复运行（数据未变）
    得到逐字一致的指纹。
    """
    member_rows = db.execute(
        select(Member.member_no, Member.consent).order_by(Member.member_no)
    ).all()
    member_payload = "|".join(f"{no}:{1 if consent else 0}" for no, consent in member_rows)
    member_hash = _hash(["members", str(len(member_rows)), member_payload])

    order_rows = db.execute(
        select(
            OrderFact.order_no,
            OrderFact.member_id,
            OrderFact.amount,
            OrderFact.ordered_at,
            OrderFact.coupon_issued,
            OrderFact.coupon_redeemed,
        ).order_by(OrderFact.order_no)
    ).all()
    order_payload = "|".join(
        "{}:{}:{}:{}:{}:{}".format(
            order_no,
            member_id,
            f"{float(amount):.2f}",
            ordered_at.isoformat(),
            1 if issued else 0,
            1 if redeemed else 0,
        )
        for order_no, member_id, amount, ordered_at, issued, redeemed in order_rows
    )
    order_hash = _hash(["orders", str(len(order_rows)), order_payload])

    return _hash(
        [
            FINGERPRINT_VERSION,
            f"as_of={as_of.isoformat()}",
            f"k={k_value}",
            f"random_state={random_state}",
            f"members={member_hash}",
            f"orders={order_hash}",
        ]
    )


def find_replayable_run(db: Session, fingerprint: str) -> SegmentRun | None:
    """找同一指纹下可复用的有效批次（失败批次不算，允许补数修复后重跑）。"""
    return db.scalar(
        select(SegmentRun)
        .where(
            SegmentRun.input_fingerprint == fingerprint,
            SegmentRun.status != "failed",
        )
        .order_by(SegmentRun.id.asc())
    )


# ---------------------------------------------------------------------------
# 整批校验
# ---------------------------------------------------------------------------

def validate_run_result(db: Session, run: SegmentRun) -> dict:
    """对一个已完成的批次做整批校验，返回结构化报告。

    校验维度：
    1. 结果快照完整（clusters / assignments / member_count）；
    2. 名单覆盖：assignments 人数 == 会员主数据人数，且会员号一一对应、无重复；
    3. 订单归属：订单事实的 member_id 全部落在本批次名单内；
    4. 簇人数加总：各簇 member_count 之和 == 名单人数；
    5. 簇内明细：每个簇 assignments 数 == 簇画像 member_count；
    6. 可触达人数：簇 reachable_count == 名单中 consent=True 的实际人数。
    """
    checks: list[dict] = []

    def add_check(name: str, ok: bool, expected, actual, detail: str | None = None) -> None:
        checks.append(
            {
                "name": name,
                "ok": bool(ok),
                "expected": expected,
                "actual": actual,
                "detail": detail,
            }
        )

    result = run.result if isinstance(run.result, dict) else None
    clusters = (result or {}).get("clusters") or []
    assignments = (result or {}).get("assignments") or []

    snapshot_ok = bool(result) and bool(clusters) and bool(assignments)
    add_check(
        "result_snapshot",
        snapshot_ok,
        "clusters/assignments 非空",
        f"clusters={len(clusters)}, assignments={len(assignments)}",
    )
    if not snapshot_ok:
        return _build_report(checks)

    # --- 会员覆盖 ---
    db_member_ids = set(db.scalars(select(Member.id)).all())
    assignment_member_ids = [int(item["member_id"]) for item in assignments]
    assignment_set = set(assignment_member_ids)
    add_check(
        "member_coverage",
        len(assignment_member_ids) == len(assignment_set)
        and assignment_set == db_member_ids,
        len(db_member_ids),
        len(assignment_set),
        detail=(
            None
            if assignment_set == db_member_ids
            else f"名单缺 {len(db_member_ids - assignment_set)} 人 / 多 {len(assignment_set - db_member_ids)} 人"
        ),
    )

    # --- 订单归属 ---
    order_total = db.scalar(select(func.count()).select_from(OrderFact)) or 0
    orphan_orders = db.scalar(
        select(func.count())
        .select_from(OrderFact)
        .where(OrderFact.member_id.notin_(assignment_set))
    ) or 0
    add_check(
        "order_ownership",
        orphan_orders == 0 and assignment_set.issubset(db_member_ids),
        order_total,
        order_total - orphan_orders,
        detail=None if orphan_orders == 0 else f"{orphan_orders} 笔订单不属于本批次名单",
    )

    # --- 簇人数加总 ---
    profile_sum = sum(int(c.get("member_count") or 0) for c in clusters)
    add_check(
        "cluster_member_sum",
        profile_sum == len(assignments),
        len(assignments),
        profile_sum,
    )

    # --- 簇内明细 + 可触达人数 ---
    consent_by_member = dict(db.execute(select(Member.id, Member.consent)).all())
    per_cluster: dict[str, list[int]] = {}
    for item in assignments:
        per_cluster.setdefault(str(item["cluster_key"]), []).append(int(item["member_id"]))

    cluster_ok = True
    reachable_ok = True
    cluster_lines = []
    for cluster in clusters:
        key = str(cluster["cluster_key"])
        member_ids = per_cluster.get(key, [])
        count_match = len(member_ids) == int(cluster.get("member_count") or 0)
        reachable_actual = sum(1 for mid in member_ids if consent_by_member.get(mid))
        reachable_match = reachable_actual == int(cluster.get("reachable_count") or 0)
        cluster_ok = cluster_ok and count_match
        reachable_ok = reachable_ok and reachable_match
        cluster_lines.append(
            {
                "cluster_key": key,
                "label": cluster.get("label"),
                "member_count": int(cluster.get("member_count") or 0),
                "assignment_count": len(member_ids),
                "reachable_count": int(cluster.get("reachable_count") or 0),
                "reachable_actual": reachable_actual,
                "count_match": count_match,
                "reachable_match": reachable_match,
            }
        )
    add_check("cluster_assignment_detail", cluster_ok, "逐簇一致", "见 clusters")
    add_check("cluster_reachable_detail", reachable_ok, "逐簇一致", "见 clusters")

    return _build_report(checks, cluster_lines)


def _build_report(checks: list[dict], cluster_lines: list[dict] | None = None) -> dict:
    return {
        "ok": all(item["ok"] for item in checks),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "clusters": cluster_lines or [],
    }


def assert_valid(run: SegmentRun) -> dict:
    """取批次已存的校验报告，未通过则抛业务错误（不切换当前版本）。"""
    report = run.validation_report if isinstance(run.validation_report, dict) else None
    if not report or not report.get("ok"):
        raise AppError(
            ErrorCode.BATCH_INVALID,
            "整批校验未通过，已保留原当前版本；请修复数据后重新跑分群",
            409,
            report,
        )
    return report


# ---------------------------------------------------------------------------
# 当前版本切换
# ---------------------------------------------------------------------------

def activate_run(db: Session, run: SegmentRun) -> SegmentRun:
    """把通过校验的批次设为当前版本（单事务，旧批次全部保留）。"""
    if run.status != "completed" or not run.result:
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成，无法设为当前版本", 409)
    assert_valid(run)
    now = datetime.now(timezone.utc)
    db.execute(
        update(SegmentRun)
        .where(SegmentRun.is_current.is_(True))
        .values(is_current=False, current_since=None)
    )
    run.is_current = True
    run.current_since = now
    db.commit()
    db.refresh(run)
    return run


def get_current_run(db: Session) -> SegmentRun | None:
    return db.scalar(select(SegmentRun).where(SegmentRun.is_current.is_(True)))


# ---------------------------------------------------------------------------
# 三方对账：会员 / 订单 / 簇人数
# ---------------------------------------------------------------------------

def reconcile_run(db: Session, run: SegmentRun) -> dict:
    """会员、订单、簇人数是否对得上的只读对账结果。"""
    if run.status != "completed" or not run.result:
        raise AppError(ErrorCode.RUN_NOT_READY, "分群批次尚未完成，无法对账", 409)

    member_total = db.scalar(select(func.count()).select_from(Member)) or 0
    order_total = db.scalar(select(func.count()).select_from(OrderFact)) or 0
    order_amount = db.scalar(select(func.coalesce(func.sum(OrderFact.amount), 0))) or 0
    assignments = run.result.get("assignments") or []
    clusters = run.result.get("clusters") or []

    cluster_rows = []
    cluster_sum = 0
    reachable_sum = 0
    for cluster in clusters:
        key = str(cluster["cluster_key"])
        assignment_count = sum(1 for item in assignments if str(item.get("cluster_key")) == key)
        member_count = int(cluster.get("member_count") or 0)
        reachable = int(cluster.get("reachable_count") or 0)
        cluster_sum += member_count
        reachable_sum += reachable
        cluster_rows.append(
            {
                "cluster_key": key,
                "label": cluster.get("label"),
                "kind": cluster.get("kind"),
                "profile_member_count": member_count,
                "assignment_count": assignment_count,
                "match": member_count == assignment_count,
                "reachable_count": reachable,
                "gmv_total": cluster.get("gmv_total"),
                "gmv_share": cluster.get("gmv_share"),
            }
        )

    report = run.validation_report if isinstance(run.validation_report, dict) else None
    return {
        "run_id": run.id,
        "run_no": run.run_no,
        "is_current": run.is_current,
        "status": run.status,
        "totals": {
            "members_in_db": int(member_total),
            "members_in_run": int(run.member_count or len(assignments)),
            "assignments": len(assignments),
            "orders_in_db": int(order_total),
            "order_gmv": round(float(order_amount), 2),
            "cluster_profile_sum": cluster_sum,
            "reachable_sum": reachable_sum,
        },
        "checks": (report or {}).get("checks", []),
        "validation_ok": bool(report and report.get("ok")),
        "clusters": cluster_rows,
    }
