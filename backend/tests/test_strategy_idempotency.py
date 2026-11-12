"""策略导出幂等与预算占用：重复导出不新增触达记录、不重复占预算。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models import Strategy
from app.services import segment_service, strategy_service


@pytest.fixture()
def completed_run(db, users, payload_factory):
    from tests.conftest import make_dataset

    make_dataset(db, member_count=120)
    run, _ = segment_service.create_run(db, payload_factory(), users["analyst"])
    return run


def _make_strategy(db, run, user):
    payload = SimpleNamespace(run_id=run.id, total_budget=8000, name=None)
    return strategy_service.create_strategy(db, payload, user)


def _export_payload(cluster_key: str, channel: str = "企微", idem: str | None = None):
    return SimpleNamespace(
        cluster_key=cluster_key, channel=channel, note=None, idempotency_key=idem
    )


def test_duplicate_export_dedups_and_keeps_budget_once(db, users, completed_run):
    strategy = _make_strategy(db, completed_run, users["admin"])
    cluster_key = completed_run.result["clusters"][0]["cluster_key"]

    first = strategy_service.record_export(
        db, strategy, _export_payload(cluster_key, idem="key-1"), users["analyst"]
    )
    assert first["deduplicated"] is False

    # 同簇同渠道再来一次（补录重跑后的重复动作）：复用同一条触达记录
    second = strategy_service.record_export(
        db, strategy, _export_payload(cluster_key, idem="key-2"), users["analyst"]
    )
    assert second["deduplicated"] is True
    assert second["entry"]["id"] == first["entry"]["id"]

    db.refresh(strategy)
    export_entries = [e for e in strategy.touch_log if e["kind"] == "export"]
    assert len(export_entries) == 1  # 没有新增触达记录

    usage = strategy_service._budget_usage(strategy)
    assert usage["raw_export_count"] == 1
    assert usage["duplicate_export_count"] == 0
    assert usage["touched_cluster_count"] == 1
    # 同簇只占一次预算
    allocation = next(
        a for a in strategy.allocations if a["cluster_key"] == cluster_key
    )
    assert usage["occupied_budget"] == float(allocation["budget"])
    assert usage["remaining_budget"] == 8000 - float(allocation["budget"])


def test_idempotency_key_alone_dedups(db, users, completed_run):
    strategy = _make_strategy(db, completed_run, users["admin"])
    cluster_key = completed_run.result["clusters"][1]["cluster_key"]

    first = strategy_service.record_export(
        db, strategy, _export_payload(cluster_key, channel="短信", idem="stable-key"),
        users["analyst"],
    )
    # 即使渠道不同，相同幂等键也视为同一动作
    second = strategy_service.record_export(
        db, strategy, _export_payload(cluster_key, channel="企微", idem="stable-key"),
        users["analyst"],
    )
    assert second["deduplicated"] is True
    assert second["entry"]["id"] == first["entry"]["id"]
    db.refresh(strategy)
    assert len([e for e in strategy.touch_log if e["kind"] == "export"]) == 1


def test_different_clusters_accumulate_budget_without_double_count(db, users, completed_run):
    strategy = _make_strategy(db, completed_run, users["admin"])
    keys = [c["cluster_key"] for c in completed_run.result["clusters"][:2]]

    strategy_service.record_export(
        db, strategy, _export_payload(keys[0], channel="企微"), users["analyst"]
    )
    strategy_service.record_export(
        db, strategy, _export_payload(keys[1], channel="企微"), users["analyst"]
    )
    # 第一个簇重复导出
    strategy_service.record_export(
        db, strategy, _export_payload(keys[0], channel="短信"), users["analyst"]
    )

    db.refresh(strategy)
    usage = strategy_service._budget_usage(strategy)
    # 实际触达 2 个簇，原始导出动作 3 次（1 次重复）
    assert usage["touched_cluster_count"] == 2
    assert usage["raw_export_count"] == 3
    assert usage["duplicate_export_count"] == 1

    expected = sum(
        float(a["budget"])
        for a in strategy.allocations
        if a["cluster_key"] in keys
    )
    assert usage["occupied_budget"] == expected
    assert usage["occupied_budget"] <= 8000
    # 占用率与剩余预算自洽
    assert usage["remaining_budget"] == round(8000 - expected, 2)
    assert 0 < usage["occupancy_rate"] <= 1


def test_published_strategy_stays_on_historical_run(db, users, completed_run):
    """已发布策略锁定旧批次 run_id；新批次成为当前版本后策略仍指向旧名单。"""
    from app.models import Member, OrderFact
    from datetime import timedelta

    strategy = _make_strategy(db, completed_run, users["admin"])
    strategy_service.publish_strategy(db, strategy, "发布到门店券核销")
    old_run_id = strategy.run_id

    # 补录订单后产生新当前批次
    first_member = db.query(Member).first()
    db.add(
        OrderFact(
            order_no="OB000999",
            member_id=first_member.id,
            store_code=first_member.store_code,
            amount=99.0,
            ordered_at=completed_run.as_of - timedelta(days=1),
            coupon_issued=False,
            coupon_redeemed=False,
            coupon_discount=0,
        )
    )
    db.commit()
    payload = SimpleNamespace(k="auto", as_of=completed_run.as_of, name=None)
    new_run, replayed = segment_service.create_run(db, payload, users["analyst"])
    assert replayed is False
    assert new_run.is_current is True

    db.refresh(strategy)
    # 新批次在任务 session 提交，主 session 的身份映射需失效后再读 run 指针
    db.expire_all()
    # 已发布策略的 run_id 不变，仍指向旧批次旧名单
    assert strategy.run_id == old_run_id
    serialized = strategy_service.serialize_strategy(db, strategy)
    assert serialized["run_id"] == old_run_id
    assert serialized["run_is_current"] is False
    assert serialized["status"] == "published"
