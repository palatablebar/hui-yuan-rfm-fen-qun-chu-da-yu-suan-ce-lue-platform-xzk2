"""端到端测试夹具：SQLite 内存库 + 可控的会员/订单数据集 + 同步分群。

不依赖 PostgreSQL / Redis / Celery：把 ``run_segment_task.delay`` 替换为同步执行，
分群走与生产完全相同的 rfm_engine + segment_service 代码路径。
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import pytest

# 必须在导入 app.* 之前指向 SQLite，避免触发 PostgreSQL 连接配置
os.environ.setdefault("DB_HOST", "localhost")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.config.database as db_config  # noqa: E402
import app.models  # noqa: E402,F401  注册全部模型
from app.models import Member, OrderFact, User  # noqa: E402
from app.utils.password import hash_password  # noqa: E402

TEST_REFERENCE = date(2026, 11, 12)


@pytest.fixture()
def db():
    # StaticPool + 单连接：所有 session（含同步任务里开的 session）共享同一个
    # 内存库，避免 QueuePool 下第二个连接拿到空白 in-memory database。
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_config.Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()

    # 让所有业务代码共用同一个测试 session 工厂
    db_config.SessionLocal = TestingSession
    import app.middlewares.audit_logger as audit_middleware
    import app.tasks.segment_task as segment_task_module

    audit_middleware.SessionLocal = TestingSession

    def _sync_delay(run_id: int):
        task_session = TestingSession()
        try:
            from app.services import segment_service

            run = task_session.get(app.models.SegmentRun, int(run_id))
            segment_service.execute_run_sync(task_session, run)
        finally:
            task_session.close()
        return None

    segment_task_module.run_segment_task.delay = staticmethod(_sync_delay)

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def users(db):
    rows = {}
    for email, role, name in [
        ("admin@rfmseg.io", "admin", "管理员"),
        ("analyst@rfmseg.io", "analyst", "分析师"),
        ("viewer@rfmseg.io", "viewer", "店长"),
    ]:
        user = User(
            email=email,
            display_name=name,
            role=role,
            password_hash=hash_password("Demo@2026"),
            is_active=True,
        )
        db.add(user)
        rows[role] = user
    db.commit()
    for user in rows.values():
        db.refresh(user)
    return rows


def make_dataset(session, member_count: int = 120, orders_per_member: int = 4, *, seed: int = 7):
    """构造确定性的会员 + 订单数据集，返回 (members, orders)。"""
    stores = [("S01", "拾光·人民广场店"), ("S02", "拾光·静安寺店")]
    members = []
    for i in range(member_count):
        store_code, store_name = stores[i % len(stores)]
        member = Member(
            member_no=f"M{i + 1:05d}",
            name=f"会员{i + 1:04d}",
            phone=f"138{i:08d}",
            store_code=store_code,
            store_name=store_name,
            joined_at=date(2025, 1, 1),
            consent=(i % 10 != 0),  # 约 10% 未授权
        )
        session.add(member)
        members.append(member)
    session.flush()

    orders = []
    order_seq = 1
    base = datetime(2026, 9, 1, 9, 0, 0)
    for i, member in enumerate(members):
        for j in range(orders_per_member):
            # 金额 / 时间带确定性差异，保证五分位打分有区分度
            amount = 20 + ((i * 13 + j * 7) % 180)
            ordered_at = base + timedelta(days=(i * 3 + j * 11) % 60, hours=j)
            issued = (j == orders_per_member - 1)
            redeemed = issued and (i % 3 == 0)
            order = OrderFact(
                order_no=f"O{order_seq:07d}",
                member_id=member.id,
                store_code=member.store_code,
                amount=amount,
                ordered_at=ordered_at,
                coupon_issued=issued,
                coupon_redeemed=redeemed,
                coupon_discount=10 if redeemed else 0,
            )
            session.add(order)
            orders.append(order)
            order_seq += 1
    session.commit()
    return members, orders


class _Payload:
    def __init__(self, k="auto", as_of=TEST_REFERENCE, name=None):
        self.k = k
        self.as_of = as_of
        self.name = name


@pytest.fixture()
def payload_factory():
    return _Payload
