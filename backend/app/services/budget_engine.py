"""算法 2：触达预算分配与每簇券面额建议。

口径（README §算法 2 同步说明）：
- 每簇期望基准 = 历史券核销率 × 簇客单价 × 可触达人数；
- 按期望基准排序把 5 个簇分成 3 档券面额（40 / 25 / 15 元，档位可配）；
- 每簇保底 400 元后，剩余预算以 100 元为步长做边际收益贪心：
  边际分 = 核销率 × 客单价 / 面额 × (1 - 已分配/该簇容量)，
  容量 = 可触达人数 × 面额（发得完为止）；
- 输出每簇预算、券面额、预计核销券数、预计增量 GMV 与 ROI。
"""
from __future__ import annotations

from app.constants.rfm import BUDGET_MAX, BUDGET_MIN, BUDGET_MIN_PER_CLUSTER, COUPON_TIERS


class BudgetError(RuntimeError):
    def __init__(self, message: str, code: str = "RFM-3002", detail=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def _clean_clusters(clusters: list[dict]) -> list[dict]:
    cleaned = []
    for cluster in clusters:
        cleaned.append(
            {
                "cluster_key": str(cluster["cluster_key"]),
                "label": str(cluster.get("label") or cluster["cluster_key"]),
                "kind": str(cluster.get("kind") or "STABLE_POTENTIAL"),
                "member_count": int(cluster.get("member_count") or 0),
                "reachable_count": int(cluster.get("reachable_count") or 0),
                "redemption_rate": float(cluster.get("redemption_rate") or 0.0),
                "aov": float(cluster.get("aov") or 0.0),
                "expected_base": round(float(cluster.get("expected_base") or 0.0), 2),
            }
        )
    return cleaned


def allocate_budget(
    clusters: list[dict],
    total_budget: float,
    tiers: tuple[int, ...] = COUPON_TIERS,
    min_per_cluster: int = BUDGET_MIN_PER_CLUSTER,
    step: int = 100,
) -> dict:
    total = int(round(float(total_budget)))
    if total < BUDGET_MIN or total > BUDGET_MAX:
        raise BudgetError(
            f"预算需在 {BUDGET_MIN:,} - {BUDGET_MAX:,} 元之间",
            detail={"total_budget": total},
        )
    if not clusters:
        raise BudgetError("该分群批次没有可分配的簇")
    items = _clean_clusters(clusters)
    n = len(items)
    if total < min_per_cluster * n:
        raise BudgetError(
            f"预算不足以给 {n} 个簇各保底 {min_per_cluster} 元",
            detail={"total_budget": total, "clusters": n},
        )

    # --- 1. 券面额分档：按期望基准排名取三档 ---
    ranked_index = sorted(
        range(n),
        key=lambda i: (-items[i]["expected_base"], -items[i]["aov"], items[i]["cluster_key"]),
    )
    for rank, index in enumerate(ranked_index):
        band = min(len(tiers) - 1, rank * len(tiers) // n)
        items[index]["tier_index"] = band
        items[index]["coupon_face"] = int(tiers[band])
        items[index]["tier_rank"] = rank + 1

    # --- 2. 保底 + 边际收益贪心 ---
    allocation = [min_per_cluster] * n
    capacity = [
        max(min_per_cluster, int(items[i]["reachable_count"] * items[i]["coupon_face"]))
        for i in range(n)
    ]
    remaining = total - min_per_cluster * n

    def marginal(index: int) -> float:
        item = items[index]
        face = item["coupon_face"]
        if face <= 0:
            return 0.0
        saturation = allocation[index] / capacity[index] if capacity[index] else 1.0
        return (item["redemption_rate"] * item["aov"] / face) * max(0.0, 1.0 - saturation)

    steps = 0
    while remaining >= step and steps < 20000:
        best_index = -1
        best_score = -1.0
        for index in range(n):
            if allocation[index] + step > capacity[index]:
                continue
            score = marginal(index)
            if score > best_score:
                best_score = score
                best_index = index
        if best_index < 0:
            break
        allocation[best_index] += step
        remaining -= step
        steps += 1

    # 余数（不足一个步长）给当前边际最高的、容量未满的簇
    if remaining > 0:
        candidates = [i for i in range(n) if allocation[i] + remaining <= capacity[i]]
        if candidates:
            target = max(candidates, key=marginal)
            allocation[target] += remaining
        else:  # 全满：把余数给容量尚可的簇（封顶），再不行并入最大簇
            target = max(range(n), key=lambda i: capacity[i] - allocation[i])
            allocation[target] += remaining

    # --- 3. 结果 ---
    allocations = []
    sum_budget = 0
    sum_redemptions = 0.0
    sum_gmv = 0.0
    total_reachable = 0
    for index, item in enumerate(items):
        face = item["coupon_face"]
        budget = allocation[index]
        coupons = budget / face if face else 0.0
        redemptions = min(float(item["reachable_count"]), coupons) * item["redemption_rate"]
        gmv = redemptions * item["aov"]
        allocations.append(
            {
                **item,
                "budget": int(budget),
                "budget_share": round(budget / total, 4) if total else 0.0,
                "coupon_face": face,
                "coupon_count": round(coupons, 1),
                "redeemable_coupons": min(item["reachable_count"], round(coupons, 1)),
                "expected_redemptions": round(redemptions, 1),
                "expected_gmv": round(gmv, 2),
                "roi": round(gmv / budget, 3) if budget else 0.0,
                "saturation": round(budget / capacity[index], 3) if capacity[index] else 0.0,
            }
        )
        sum_budget += budget
        sum_redemptions += redemptions
        sum_gmv += gmv
        total_reachable += item["reachable_count"]

    allocations.sort(key=lambda item: item["cluster_key"])
    for item in allocations:  # 排序后 tiers 展示用
        item.pop("tier_index", None)
    tiers_used = sorted({item["coupon_face"] for item in allocations}, reverse=True)
    return {
        "allocations": allocations,
        "totals": {
            "budget": int(sum_budget),
            "expected_redemptions": round(sum_redemptions, 1),
            "expected_gmv": round(sum_gmv, 2),
            "roi": round(sum_gmv / sum_budget, 3) if sum_budget else 0.0,
            "reachable_members": total_reachable,
            "member_count": sum(item["member_count"] for item in allocations),
        },
        "tiers_used": tiers_used,
        "tier_policy": "按簇期望基准排序分三档（40/25/15 元），每簇保底 400 元后按边际收益贪心分配",
        "step": step,
    }
