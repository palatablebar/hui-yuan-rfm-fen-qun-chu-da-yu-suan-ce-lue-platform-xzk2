"""HTTP 层集成测试：新接口的真实请求/响应契约与 RBAC。

用 FastAPI TestClient 打完整中间件链（Auth / RateLimit / Audit / 错误信封），
数据库依赖覆盖到测试 session 工厂。
"""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config.database import get_db
from app.main import app
from app.models import Member, OrderFact, SegmentRun
from app.services import segment_service, strategy_service
from app.utils.jwt import create_access_token


@pytest.fixture()
def client(db, monkeypatch):
    import app.config.database as db_config

    # lifespan 里的 init_db/seed 面向 PostgreSQL，测试环境已自行建表，直接跳过
    monkeypatch.setattr("app.main.init_db", lambda: None)
    monkeypatch.setattr("app.main.settings", SimpleNamespace(SEED_DEMO=False))

    def _override_get_db():
        # 每个请求开一个新 session，与生产 get_db 行为一致；共用同一内存库
        session = db_config.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _auth_headers(users, role: str) -> dict:
    token = create_access_token(users[role])
    return {"Authorization": f"Bearer {token}"}


def test_full_batch_lifecycle_over_http(client, db, users):
    from tests.conftest import make_dataset

    make_dataset(db, member_count=120)
    headers = _auth_headers(users, "analyst")

    # 1. 创建分群 → 201，自动成为当前版本
    resp = client.post("/segments/runs", json={"k": "auto", "as_of": "2026-11-12"}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["replayed"] is False
    run_id = body["run"]["id"]
    assert body["run"]["is_current"] is True
    assert body["run"]["validation_ok"] is True

    # 2. 当前版本接口
    current = client.get("/segments/runs/current", headers=headers).json()["run"]
    assert current["id"] == run_id

    # 3. 相同输入重复创建 → 200 幂等复用，不新增批次
    replay = client.post("/segments/runs", json={"k": "auto", "as_of": "2026-11-12"}, headers=headers)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["run"]["id"] == run_id
    assert db.query(SegmentRun).count() == 1

    # 4. 对账接口：会员 / 订单 / 簇人数对得上
    recon = client.get(f"/segments/runs/{run_id}/reconciliation", headers=headers).json()
    assert recon["validation_ok"] is True
    assert recon["totals"]["members_in_db"] == 120
    assert recon["totals"]["cluster_profile_sum"] == 120
    assert all(row["match"] for row in recon["clusters"])

    # 5. 补录订单 → 新批次并切换当前版本，历史批次保留
    member = db.query(Member).first()
    db.add(
        OrderFact(
            order_no="OBHTTP001",
            member_id=member.id,
            store_code=member.store_code,
            amount=77.0,
            ordered_at=datetime(2026, 11, 10),
            coupon_issued=False,
            coupon_redeemed=False,
            coupon_discount=0,
        )
    )
    db.commit()
    resp2 = client.post("/segments/runs", json={"k": "auto", "as_of": "2026-11-12"}, headers=headers)
    assert resp2.status_code == 201
    new_run = resp2.json()["run"]
    assert new_run["id"] != run_id
    assert new_run["is_current"] is True
    assert db.query(SegmentRun).count() == 2

    # 6. 手动激活历史批次
    activated = client.post(f"/segments/runs/{run_id}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["run"]["is_current"] is True
    current_after = client.get("/segments/runs/current", headers=headers).json()["run"]
    assert current_after["id"] == run_id


def test_viewer_cannot_create_or_activate(client, db, users):
    from tests.conftest import make_dataset

    make_dataset(db, member_count=120)
    viewer_headers = _auth_headers(users, "viewer")

    resp = client.post(
        "/segments/runs", json={"k": "auto", "as_of": "2026-11-12"}, headers=viewer_headers
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "RFM-1003"

    analyst_headers = _auth_headers(users, "analyst")
    created = client.post(
        "/segments/runs", json={"k": "auto", "as_of": "2026-11-12"}, headers=analyst_headers
    ).json()["run"]

    blocked = client.post(f"/segments/runs/{created['id']}/activate", headers=viewer_headers)
    assert blocked.status_code == 403


def test_export_idempotency_over_http(client, db, users):
    from tests.conftest import make_dataset

    make_dataset(db, member_count=120)
    run, _ = segment_service.create_run(
        db, SimpleNamespace(k="auto", as_of=None, name=None), users["analyst"]
    )
    strategy = strategy_service.create_strategy(
        db, SimpleNamespace(run_id=run.id, total_budget=8000, name=None), users["admin"]
    )
    headers = _auth_headers(users, "analyst")
    cluster_key = run.result["clusters"][0]["cluster_key"]

    first = client.post(
        f"/strategies/{strategy.id}/exports",
        json={"cluster_key": cluster_key, "channel": "企微", "idempotency_key": "k-1"},
        headers=headers,
    )
    assert first.status_code == 201
    assert first.json()["deduplicated"] is False

    # 重复请求：同簇 + 同渠道 → 去重，复用同一条触达记录
    second = client.post(
        f"/strategies/{strategy.id}/exports",
        json={"cluster_key": cluster_key, "channel": "企微", "idempotency_key": "k-2"},
        headers=headers,
    )
    assert second.json()["deduplicated"] is True
    assert second.json()["entry"]["id"] == first.json()["entry"]["id"]

    detail = client.get(f"/strategies/{strategy.id}", headers=headers).json()["strategy"]
    exports = [entry for entry in detail["touch_log"] if entry["kind"] == "export"]
    assert len(exports) == 1  # 没有新增触达记录
    # 预算只占用一次
    expected_budget = float(
        next(a for a in detail["allocations"] if a["cluster_key"] == cluster_key)["budget"]
    )
    assert detail["budget_usage"]["occupied_budget"] == expected_budget
    assert detail["run_is_current"] is True


def test_reconciliation_409_for_unfinished_run(client, db, users):
    headers = _auth_headers(users, "analyst")
    run = SegmentRun(
        run_no="SEG-20990101-001",
        name="未完成",
        status="queued",
        k_requested="auto",
        as_of=date(2099, 1, 1),
        random_state=5741,
    )
    db.add(run)
    db.commit()
    resp = client.get(f"/segments/runs/{run.id}/reconciliation", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "RFM-3003"
