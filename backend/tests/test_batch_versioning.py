"""批次版本化核心保证（对应订单补录重跑场景）。

覆盖：
1. 首次跑分群 → 整批校验通过 → 自动成为当前版本；
2. 数据不变重复运行 → 命中输入指纹，复用同一批次，不新增名单；
3. 订单补录（真实改变数据）→ 产生新批次，旧批次保留为历史版本，当前版本切换；
4. 整批校验失败 → 新批次 failed/非当前，原当前版本保持不变；
5. 手动切换历史批次为当前版本；
6. 对账接口：会员 / 订单 / 簇人数对得上。
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.constants.error_codes import AppError, ErrorCode
from app.models import OrderFact, SegmentRun
from app.services import batch_versioning, segment_service


def _create_run(db, users, payload_factory):
    run, replayed = segment_service.create_run(
        db, payload_factory(), users["analyst"]
    )
    return run, replayed


def test_first_run_validates_and_becomes_current(db, users, payload_factory):
    from tests.conftest import make_dataset

    make_dataset(db, member_count=120)
    run, replayed = _create_run(db, users, payload_factory)

    assert replayed is False
    assert run.status == "completed"
    assert run.is_current is True
    assert run.current_since is not None
    assert run.input_fingerprint and len(run.input_fingerprint) == 64
    report = run.validation_report
    assert report["ok"] is True
    names = {check["name"] for check in report["checks"]}
    assert {
        "result_snapshot",
        "member_coverage",
        "order_ownership",
        "cluster_member_sum",
        "cluster_assignment_detail",
        "cluster_reachable_detail",
    }.issubset(names)
    # 簇人数加总 == 会员人数
    profile_sum = sum(c["member_count"] for c in run.result["clusters"])
    assert profile_sum == run.member_count == 120


def test_identical_replay_dedups_same_batch(db, users, payload_factory):
    from tests.conftest import make_dataset

    make_dataset(db, member_count=120)
    first, replayed_first = _create_run(db, users, payload_factory)
    assert replayed_first is False
    first_fingerprint = first.input_fingerprint

    # 完全相同的输入再跑一次：必须复用，不新增批次
    second, replayed_second = _create_run(db, users, payload_factory)
    assert replayed_second is True
    assert second.id == first.id
    assert second.input_fingerprint == first_fingerprint

    total_runs = db.scalar(select(func.count()).select_from(SegmentRun))
    assert total_runs == 1
    # 名单也没有新增（同一 result 快照对象）
    assert len(second.result["assignments"]) == 120


def test_fingerprint_changes_only_when_data_changes(db, users, payload_factory):
    from tests.conftest import make_dataset

    members, orders = make_dataset(db, member_count=120)
    run, _ = _create_run(db, users, payload_factory)
    fp_before = run.input_fingerprint

    fp_after = batch_versioning.input_fingerprint(
        db, run.as_of, run.k_requested, run.random_state
    )
    assert fp_after == fp_before

    # 补录一笔新订单 → 指纹必须变化
    last_order = orders[-1]
    new_order = OrderFact(
        order_no="O9999999",
        member_id=members[0].id,
        store_code=members[0].store_code,
        amount=88.8,
        ordered_at=last_order.ordered_at + timedelta(days=1),
        coupon_issued=False,
        coupon_redeemed=False,
        coupon_discount=0,
    )
    db.add(new_order)
    db.commit()
    fp_backfilled = batch_versioning.input_fingerprint(
        db, run.as_of, run.k_requested, run.random_state
    )
    assert fp_backfilled != fp_before


def test_backfill_creates_new_batch_and_switches_current(db, users, payload_factory):
    from tests.conftest import make_dataset

    members, _ = make_dataset(db, member_count=120)
    old_run, _ = _create_run(db, users, payload_factory)
    assert old_run.is_current is True

    # 会员订单补录：给前 10 个会员各补一笔订单
    for i in range(10):
        db.add(
            OrderFact(
                order_no=f"OB{i:06d}",
                member_id=members[i].id,
                store_code=members[i].store_code,
                amount=120.0 + i,
                ordered_at=old_run.as_of  # type: ignore[operator]
                - timedelta(days=2),
                coupon_issued=True,
                coupon_redeemed=(i % 2 == 0),
                coupon_discount=15 if i % 2 == 0 else 0,
            )
        )
    db.commit()

    new_run, replayed = _create_run(db, users, payload_factory)
    assert replayed is False
    assert new_run.id != old_run.id

    # 历史批次保留，新批次成为当前版本，同一时刻只有一个 current
    db.refresh(old_run)
    db.refresh(new_run)
    assert old_run.is_current is False
    assert new_run.is_current is True
    current_runs = db.scalar(
        select(func.count()).select_from(SegmentRun).where(SegmentRun.is_current.is_(True))
    )
    assert current_runs == 1
    total_runs = db.scalar(select(func.count()).select_from(SegmentRun))
    assert total_runs == 2
    # 两个批次都完整保留各自的名单快照
    assert len(old_run.result["assignments"]) == 120
    assert len(new_run.result["assignments"]) == 120


def test_failed_validation_keeps_previous_current(db, users, payload_factory, monkeypatch):
    """整批校验失败：新批次保留报告但不切换，原当前版本继续在线上。

    分群任务在独立线程执行，monkeypatch 进不去，因此用真实数据故障触发：
    让 validate_run_result 的簇人数加总检查必然失败（改坏簇画像人数）。
    """
    from tests.conftest import make_dataset
    from app.services import segment_service as ss

    make_dataset(db, member_count=120)
    good_run, _ = _create_run(db, users, payload_factory)
    assert good_run.is_current is True

    # 补录订单制造新指纹
    db.add(
        OrderFact(
            order_no="OB000001",
            member_id=1,
            store_code="S01",
            amount=50,
            ordered_at=good_run.as_of - timedelta(days=1),  # type: ignore[operator]
            coupon_issued=False,
            coupon_redeemed=False,
            coupon_discount=0,
        )
    )
    db.commit()

    # 分群任务在 worker 线程执行：直接改模块全局（非线程局部），让该批次产出的
    # 簇画像人数与名单对不上，触发真实的整批校验失败路径。
    from app.services import rfm_engine

    original_run_seg = rfm_engine.run_segmentation

    def _tampered_run_segmentation(*args, **kwargs):
        result = original_run_seg(*args, **kwargs)
        result["clusters"][0]["member_count"] += 5
        return result

    rfm_engine.run_segmentation = _tampered_run_segmentation
    try:
        bad_run, replayed = _create_run(db, users, payload_factory)
    finally:
        rfm_engine.run_segmentation = original_run_seg

    assert replayed is False
    assert bad_run.id != good_run.id
    db.refresh(bad_run)
    # 失败批次保留、带校验报告，但不是当前版本
    assert bad_run.is_current is False
    assert bad_run.validation_report is not None
    assert bad_run.validation_report["ok"] is False
    failed_checks = {c["name"]: c for c in bad_run.validation_report["checks"]}
    assert failed_checks["cluster_member_sum"]["ok"] is False
    # 原当前版本仍然在线上服务
    db.refresh(good_run)
    assert good_run.is_current is True
    assert segment_service.get_current(db).id == good_run.id

    # 校验未通过的批次不允许手动激活
    with pytest.raises(AppError) as exc_info:
        segment_service.activate_current_run(db, bad_run.id)
    assert exc_info.value.code == ErrorCode.BATCH_INVALID


def test_manual_activate_historical_run(db, users, payload_factory):
    from tests.conftest import make_dataset

    members, _ = make_dataset(db, member_count=120)
    first, _ = _create_run(db, users, payload_factory)

    for i in range(5):
        db.add(
            OrderFact(
                order_no=f"OB{i:06d}",
                member_id=members[i].id,
                store_code=members[i].store_code,
                amount=66.0,
                ordered_at=first.as_of - timedelta(days=3),  # type: ignore[operator]
                coupon_issued=False,
                coupon_redeemed=False,
                coupon_discount=0,
            )
        )
    db.commit()
    second, _ = _create_run(db, users, payload_factory)
    assert second.is_current is True
    db.refresh(first)
    assert first.is_current is False

    # 手动切回历史批次
    switched = segment_service.activate_current_run(db, first.id)
    assert switched.is_current is True
    db.refresh(first)
    db.refresh(second)
    assert first.is_current is True
    assert second.is_current is False
    assert segment_service.get_current(db).id == first.id


def test_reconciliation_reports_consistent_counts(db, users, payload_factory):
    from tests.conftest import make_dataset

    members, orders = make_dataset(db, member_count=120, orders_per_member=4)
    run, _ = _create_run(db, users, payload_factory)

    recon = segment_service.get_reconciliation(db, run.id)
    assert recon["validation_ok"] is True
    assert recon["totals"]["members_in_db"] == 120
    assert recon["totals"]["members_in_run"] == 120
    assert recon["totals"]["assignments"] == 120
    assert recon["totals"]["orders_in_db"] == len(orders)
    assert recon["totals"]["cluster_profile_sum"] == 120
    # 每个簇画像人数 == 该簇 assignments 数
    assert all(row["match"] for row in recon["clusters"])
    reachable_expected = sum(1 for m in members if m.consent)
    assert recon["totals"]["reachable_sum"] == reachable_expected
