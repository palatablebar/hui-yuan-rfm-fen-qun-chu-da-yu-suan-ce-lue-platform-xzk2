"""幂等演示 seed：拾光咖啡 8 门店 / 600 会员 / 2400 订单 / 1 次分群 / 3 账号。

幂等策略：
- 用户按 email、会员按 member_no、订单按 order_no 做自然键 upsert（已存在则不改）；
- 演示分群批次按固定 run_no 判重，已存在则不重算；
- 结束时打印一行固定格式 SEED_SUMMARY，连续两次运行逐字一致。
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.config.database import SessionLocal
from app.constants.roles import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER
from app.constants.rfm import REFERENCE_DATE, RANDOM_STATE
from app.models import Member, OrderFact, SegmentRun, User
from app.services import segment_service
from app.utils.logger import log_event
from app.utils.password import hash_password
from scripts.seed_data import STORES, build_demo_dataset

DEMO_PASSWORD = "Demo@2026"
SEED_RUN_NO = "SEG-20261112-001"

DEMO_USERS = [
    {
        "email": "admin@rfmseg.io",
        "display_name": "沈知远",
        "role": ROLE_ADMIN,
    },
    {
        "email": "analyst@rfmseg.io",
        "display_name": "林晚照",
        "role": ROLE_ANALYST,
    },
    {
        "email": "viewer@rfmseg.io",
        "display_name": "周启明",
        "role": ROLE_VIEWER,
    },
]


def _ensure_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for spec in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == spec["email"]))
        if user is None:
            user = User(
                email=spec["email"],
                display_name=spec["display_name"],
                role=spec["role"],
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
            )
            db.add(user)
            db.flush()
        users[spec["role"]] = user
    db.commit()
    return users


def _ensure_members(db, member_rows: list[dict]) -> None:
    existing = set(db.scalars(select(Member.member_no)).all())
    pending = []
    for row in member_rows:
        if row["member_no"] in existing:
            continue
        pending.append(
            Member(
                member_no=row["member_no"],
                name=row["name"],
                phone=row["phone"],
                store_code=row["store_code"],
                store_name=row["store_name"],
                joined_at=row["joined_at"],
                consent=row["consent"],
            )
        )
    if pending:
        db.add_all(pending)
    db.commit()


def _ensure_orders(db, order_rows: list[dict]) -> None:
    member_map = {
        member_no: member_id
        for member_no, member_id in db.execute(select(Member.member_no, Member.id)).all()
    }
    existing = set(db.scalars(select(OrderFact.order_no)).all())
    pending = []
    for row in order_rows:
        if row["order_no"] in existing:
            continue
        pending.append(
            OrderFact(
                order_no=row["order_no"],
                member_id=member_map[row["member_no"]],
                store_code=row["store_code"],
                amount=row["amount"],
                ordered_at=row["ordered_at"],
                coupon_issued=row["coupon_issued"],
                coupon_redeemed=row["coupon_redeemed"],
                coupon_discount=row["coupon_discount"],
            )
        )
    if pending:
        db.add_all(pending)
    db.commit()


def _ensure_segment(db, admin: User) -> None:
    run = db.scalar(select(SegmentRun).where(SegmentRun.run_no == SEED_RUN_NO))
    if run is not None:
        return
    run = SegmentRun(
        run_no=SEED_RUN_NO,
        name="2026-11 会员 RFM 基线分群",
        status="queued",
        k_requested="auto",
        as_of=REFERENCE_DATE,
        random_state=RANDOM_STATE,
        created_by=admin.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    segment_service.execute_run_sync(db, run)


def run_seed() -> dict:
    db = SessionLocal()
    try:
        users = _ensure_users(db)
        dataset = build_demo_dataset()
        _ensure_members(db, dataset["members"])
        _ensure_orders(db, dataset["orders"])
        _ensure_segment(db, users[ROLE_ADMIN])

        member_count = db.scalar(select(func.count()).select_from(Member)) or 0
        order_count = db.scalar(select(func.count()).select_from(OrderFact)) or 0
        segment_count = db.scalar(select(func.count()).select_from(SegmentRun)) or 0
        user_count = db.scalar(select(func.count()).select_from(User)) or 0
    finally:
        db.close()

    summary = {
        "brand": "rfmseg",
        "stores": len(STORES),
        "members": int(member_count),
        "orders": int(order_count),
        "segments": int(segment_count),
        "users": int(user_count),
    }
    print(
        "SEED_SUMMARY brand={brand} stores={stores} members={members} "
        "orders={orders} segments={segments} users={users}".format(**summary),
        flush=True,
    )
    return summary


if __name__ == "__main__":
    log_event("SEED_SUMMARY_RUN", **run_seed())
