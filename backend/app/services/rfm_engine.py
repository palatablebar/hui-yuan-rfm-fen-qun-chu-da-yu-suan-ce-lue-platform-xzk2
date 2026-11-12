"""RFM 五分位打分 + 标准化 + 手写 numpy KMeans + 轮廓系数选 k。

纯 numpy 模块（不 import DB / web 框架）：seed 脚本、Celery worker 与离线调参
脚本共用同一份实现，配合固定 ``random_state`` 保证分群结果可复现。

口径：
1. 从订单事实表按会员聚合 R（距 as-of 天数，越小越好）/ F（订单数）/ M（GMV）；
2. 每个维度做等频五分位打分（1-5，R 反向），恰好每档约 20% 会员；
3. 三个分数做 z-score 标准化后进入 KMeans（k-means++ 初始化，手写迭代）；
4. k 在 3..8 之间按平均轮廓系数 ``s=(b-a)/max(a,b)`` 选最优（同分取较小 k）；
5. 按簇均值分数生成业务画像与类型（高价值沉睡 / 核心活跃 / ...）。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

import numpy as np

from app.constants.cluster_kinds import CLUSTER_KIND_META
from app.constants.rfm import (
    K_MAX,
    K_MIN,
    MIN_MEMBERS,
    RANDOM_STATE,
    SCORE_MAX,
    SCORE_MIN,
)


class SegmentationError(RuntimeError):
    """分群失败（样本不足 / 参数非法），带业务错误码。"""

    def __init__(self, message: str, code: str = "RFM-3001", detail: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


# ---------------------------------------------------------------------------
# 特征聚合
# ---------------------------------------------------------------------------

def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()


def aggregate_features(
    members: Iterable[dict],
    orders: Iterable[dict],
    as_of: date,
) -> list[dict]:
    """按会员聚合 RFM 与券历史。

    members: {member_id, member_no, name, store_code, store_name, consent, joined_at}
    orders:  {member_id, amount, ordered_at, coupon_issued, coupon_redeemed}
    """
    stats: dict[int, dict] = {}
    for order in orders:
        mid = int(order["member_id"])
        bucket = stats.setdefault(
            mid,
            {
                "frequency": 0,
                "monetary": 0.0,
                "last_order": None,
                "coupon_issued": 0,
                "coupon_redeemed": 0,
            },
        )
        amount = float(order.get("amount") or 0.0)
        ordered_at = _to_date(order.get("ordered_at"))
        bucket["frequency"] += 1
        bucket["monetary"] += amount
        if bucket["last_order"] is None or ordered_at > bucket["last_order"]:
            bucket["last_order"] = ordered_at
        if order.get("coupon_issued"):
            bucket["coupon_issued"] += 1
            if order.get("coupon_redeemed"):
                bucket["coupon_redeemed"] += 1

    features: list[dict] = []
    for member in members:
        mid = int(member["member_id"])
        bucket = stats.get(mid)
        if bucket and bucket["last_order"] is not None:
            recency_days = max((as_of - bucket["last_order"]).days, 0)
            frequency = bucket["frequency"]
            monetary = round(bucket["monetary"], 2)
        else:  # 没有任何订单的僵尸会员，给最差 R/F/M，但仍参与打分
            recency_days = 365
            frequency = 0
            monetary = 0.0
        features.append(
            {
                "member_id": mid,
                "member_no": member["member_no"],
                "name": member.get("name", ""),
                "store_code": member.get("store_code", ""),
                "store_name": member.get("store_name", ""),
                "consent": bool(member.get("consent", True)),
                "joined_at": _to_date(member.get("joined_at", as_of)).isoformat(),
                "recency_days": int(recency_days),
                "frequency": int(frequency),
                "monetary": float(monetary),
                "aov": round(monetary / frequency, 2) if frequency else 0.0,
                "coupon_issued": int(bucket["coupon_issued"]) if bucket else 0,
                "coupon_redeemed": int(bucket["coupon_redeemed"]) if bucket else 0,
            }
        )
    features.sort(key=lambda item: item["member_no"])
    return features


# ---------------------------------------------------------------------------
# 打分与标准化
# ---------------------------------------------------------------------------

def quantile_scores(values: Iterable[float], reverse: bool = False) -> np.ndarray:
    """等频五分位打分（1-5）。

    用稳定排序后的名次分档而不是 np.quantile 切点，避免大量并列值时档位失衡；
    600 人数据上每档恰好 120 人。reverse=True 用于 R（天数越小分越高）。
    """
    arr = np.asarray(list(values), dtype=float)
    n = arr.size
    if n == 0:
        return np.empty(0, dtype=float)
    if n < SCORE_MAX:
        return np.full(n, 3.0)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty(n, dtype=int)
    ranks[order] = np.arange(n)
    scores = (ranks * SCORE_MAX // n) + SCORE_MIN
    if reverse:
        scores = (SCORE_MAX + SCORE_MIN) - scores
    return scores.astype(float)


def standardize(matrix: np.ndarray) -> np.ndarray:
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return (matrix - mean) / std


# ---------------------------------------------------------------------------
# 手写 KMeans（numpy 实现，不用 sklearn）
# ---------------------------------------------------------------------------

def kmeans(
    X: np.ndarray,
    k: int,
    rng: np.random.Generator,
    max_iter: int = 300,
    tol: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray, float]:
    n = X.shape[0]
    if k < 1 or k > n:
        raise ValueError(f"invalid k={k} for n={n}")

    # --- k-means++ 初始化 ---
    centers = np.empty((k, X.shape[1]), dtype=float)
    first = int(rng.integers(n))
    centers[0] = X[first]
    closest = ((X - centers[0]) ** 2).sum(axis=1)
    for c in range(1, k):
        total = float(closest.sum())
        if total <= 0:
            idx = int(rng.integers(n))
        else:
            probs = closest / total
            idx = int(rng.choice(n, p=probs))
        centers[c] = X[idx]
        closest = np.minimum(closest, ((X - centers[c]) ** 2).sum(axis=1))

    labels = np.full(n, -1, dtype=int)
    for _ in range(max_iter):
        distances = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = distances.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for c in range(k):
            points = X[labels == c]
            if points.size:
                centers[c] = points.mean(axis=0)
            else:  # 空簇重新播种，保证不会卡死
                centers[c] = X[int(rng.integers(n))]
        shift = float(np.abs(centers).sum())
        if shift < tol:
            break

    inertia = float(((X - centers[labels]) ** 2).sum())
    return labels, centers, inertia


def silhouette_score(X: np.ndarray, labels: np.ndarray, sample: int = 600) -> float:
    """平均轮廓系数 s=(b-a)/max(a,b)，O(n^2) 距离矩阵。"""
    n = X.shape[0]
    labels = np.asarray(labels)
    unique = np.unique(labels)
    if unique.size < 2:
        return 0.0
    if n > sample:  # 自采样，固定种子以保证可复现
        rng = np.random.default_rng(RANDOM_STATE + int(unique.size))
        idx = np.sort(rng.choice(n, size=sample, replace=False))
        X = X[idx]
        labels = labels[idx]
        n = sample
    distances = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))
    scores = np.zeros(n, dtype=float)
    masks = {c: (labels == c) for c in np.unique(labels)}
    for i in range(n):
        own = masks[labels[i]]
        own_size = int(own.sum())
        if own_size <= 1:
            scores[i] = 0.0
            continue
        a = float(distances[i, own].sum() / (own_size - 1))
        b = np.inf
        for c, mask in masks.items():
            if c == labels[i]:
                continue
            b = min(b, float(distances[i, mask].mean()))
        denom = max(a, b)
        scores[i] = (b - a) / denom if denom > 0 else 0.0
    return float(np.mean(scores))


def select_k(
    X: np.ndarray,
    k_min: int = K_MIN,
    k_max: int = K_MAX,
    random_state: int = RANDOM_STATE,
) -> tuple[dict, list[dict]]:
    """k 扫描：返回最优结果与每个 k 的轮廓系数/惯性曲线。"""
    n = X.shape[0]
    upper = min(k_max, n - 1)
    sweep: list[dict] = []
    best: dict | None = None
    for k in range(k_min, upper + 1):
        rng = np.random.default_rng(random_state + k)
        labels, centers, inertia = kmeans(X, k, rng)
        silhouette = silhouette_score(X, labels)
        item = {
            "k": k,
            "silhouette": round(float(silhouette), 6),
            "inertia": round(float(inertia), 6),
            "labels": labels,
            "centers": centers,
        }
        sweep.append(item)
        if best is None or (item["silhouette"], -k) > (best["silhouette"], -best["k"]):
            best = item
    assert best is not None
    return best, [{key: value for key, value in item.items() if key not in ("labels", "centers")} for item in sweep]


# ---------------------------------------------------------------------------
# 簇画像与业务命名
# ---------------------------------------------------------------------------

def _kind_for(score_r: float, score_f: float, score_m: float) -> str:
    if score_r <= 2.45 and score_f >= 3.4 and score_m >= 3.4:
        return "HIGH_VALUE_DORMANT"
    if score_r >= 3.55 and score_f >= 3.3 and score_m >= 3.3:
        return "CORE_ACTIVE"
    if score_r >= 3.3 and score_f <= 2.4:
        return "NEW_NURTURE"
    if score_m <= 2.9 and score_f >= 2.6:
        return "PRICE_SENSITIVE"
    if score_r <= 2.6 and score_f <= 2.4:
        return "LOW_FREQ_CHURN"
    return "STABLE_POTENTIAL"


def build_cluster_profiles(
    features: list[dict],
    scores: np.ndarray,
    labels: np.ndarray,
) -> tuple[list[dict], dict[int, str]]:
    gmv_total_all = sum(item["monetary"] for item in features) or 1.0
    raw_clusters: list[dict] = []
    for raw_label in np.unique(labels):
        idx = np.where(labels == raw_label)[0]
        members = [features[i] for i in idx]
        count = len(members)
        gmv = sum(item["monetary"] for item in members)
        frequency = sum(item["frequency"] for item in members)
        coupon_issued = sum(item["coupon_issued"] for item in members)
        coupon_redeemed = sum(item["coupon_redeemed"] for item in members)
        score_means = [round(float(scores[idx, d].mean()), 3) for d in range(3)]
        kind = _kind_for(*score_means)
        meta = CLUSTER_KIND_META[kind]
        reachable = sum(1 for item in members if item["consent"])
        aov = round(gmv / frequency, 2) if frequency else 0.0
        redemption_rate = round(coupon_redeemed / coupon_issued, 4) if coupon_issued else 0.0
        expected_base = round(redemption_rate * aov * reachable, 2)
        raw_clusters.append(
            {
                "raw_label": int(raw_label),
                "kind": kind,
                "label": meta["label"],
                "short": meta["short"],
                "advice": meta["advice"],
                "member_count": count,
                "reachable_count": reachable,
                "gmv_total": round(gmv, 2),
                "gmv_share": round(gmv / gmv_total_all, 4),
                "gmv_per_member": round(gmv / count, 2),
                "aov": aov,
                "recency_mean_days": round(sum(item["recency_days"] for item in members) / count, 1),
                "frequency_mean": round(frequency / count, 2),
                "monetary_mean": round(gmv / count, 2),
                "coupon_issued": coupon_issued,
                "coupon_redeemed": coupon_redeemed,
                "redemption_rate": redemption_rate,
                "expected_base": expected_base,
                "score_means": {"r": score_means[0], "f": score_means[1], "m": score_means[2]},
            }
        )

    # 排序决定稳定簇键：先按人数降序，再按 M 均分降序
    raw_clusters.sort(
        key=lambda c: (-c["member_count"], -c["score_means"]["m"], -c["score_means"]["r"], c["kind"])
    )
    key_map: dict[int, str] = {}
    labels_order: dict[int, str] = {}
    seen: dict[str, int] = {}
    for index, cluster in enumerate(raw_clusters, start=1):
        cluster_key = f"C{index}"
        key_map[cluster["raw_label"]] = cluster_key
        labels_order[cluster["raw_label"]] = cluster_key
        cluster["cluster_key"] = cluster_key
        display = cluster["label"]
        if display in seen:
            seen[display] += 1
            cluster["label"] = f"{display}·{seen[display]}"
        else:
            seen[display] = 1
        cluster.pop("raw_label", None)
    return raw_clusters, key_map


def build_histograms(features: list[dict], scores: np.ndarray) -> dict:
    """RFM 三个维度的分数分布（1-5 档计数）与原始值 8 档直方图。"""
    score_distribution = {}
    for dim, name in enumerate(("recency", "frequency", "monetary")):
        counts = [0] * 5
        for value in scores[:, dim]:
            counts[int(value) - 1] += 1
        score_distribution[name] = counts

    raw_distribution = {}
    for dim, key in enumerate(("recency_days", "frequency", "monetary")):
        values = np.asarray([item[key] for item in features], dtype=float)
        # 右偏金额/天数用等频分箱，保证每根柱有样本；标签给真实边界
        order = np.argsort(values, kind="mergesort")
        sorted_values = values[order]
        bins = 8
        edges = [float(sorted_values[0])]
        for b in range(1, bins):
            edges.append(float(sorted_values[int(len(sorted_values) * b / bins)]))
        edges.append(float(sorted_values[-1]))
        counts = [0] * bins
        for value in values:
            slot = int(np.searchsorted(edges, value, side="right") - 1)
            slot = min(max(slot, 0), bins - 1)
            counts[slot] += 1
        raw_distribution[key] = {
            "edges": [round(edge, 2) for edge in edges],
            "counts": counts,
        }
    return {"score_distribution": score_distribution, "raw_distribution": raw_distribution}


def build_scatter(
    features: list[dict],
    labels: np.ndarray,
    key_map: dict[int, str],
    max_points: int = 240,
) -> list[dict]:
    n = len(features)
    step = max(1, n // max_points)
    points = []
    for i in range(0, n, step):
        item = features[i]
        points.append(
            {
                "member_no": item["member_no"],
                "x": item["recency_days"],
                "y": round(item["monetary"], 2),
                "cluster_key": key_map[int(labels[i])],
            }
        )
    return points


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def run_segmentation(
    members: list[dict],
    orders: list[dict],
    as_of: date | str | None = None,
    k: int | str | None = "auto",
    random_state: int = RANDOM_STATE,
) -> dict:
    from app.constants.rfm import REFERENCE_DATE

    as_of_date = _to_date(as_of) if as_of else REFERENCE_DATE
    features = aggregate_features(members, orders, as_of_date)
    if len(features) < MIN_MEMBERS:
        raise SegmentationError(
            f"会员样本不足 100 人（当前 {len(features)} 人），无法做五分位分群",
            code="RFM-3001",
            detail={"member_count": len(features), "required": MIN_MEMBERS},
        )

    recency = [item["recency_days"] for item in features]
    frequency = [item["frequency"] for item in features]
    monetary = [item["monetary"] for item in features]
    scores = np.column_stack(
        [
            quantile_scores(recency, reverse=True),
            quantile_scores(frequency),
            quantile_scores(monetary),
        ]
    )
    X = standardize(scores)

    if k in (None, "", "auto"):
        requested_k = "auto"
        best, sweep = select_k(X, k_min=K_MIN, k_max=K_MAX, random_state=random_state)
        labels = best["labels"]
        selected_k = int(best["k"])
        silhouette = float(best["silhouette"])
        inertia = float(best["inertia"])
    else:
        requested_k = int(k)
        if not (2 <= requested_k <= 8):
            raise SegmentationError("k 必须在 2-8 之间", code="RFM-2001", detail={"k": requested_k})
        rng = np.random.default_rng(random_state + requested_k)
        labels, _centers, inertia = kmeans(X, requested_k, rng)
        sweep = []
        for candidate in range(K_MIN, min(K_MAX, len(features) - 1) + 1):
            rng_c = np.random.default_rng(random_state + candidate)
            labels_c, _centers_c, inertia_c = kmeans(X, candidate, rng_c)
            sweep.append(
                {
                    "k": candidate,
                    "silhouette": round(silhouette_score(X, labels_c), 6),
                    "inertia": round(inertia_c, 6),
                }
            )
        selected_k = requested_k
        silhouette = round(silhouette_score(X, labels), 6)
        inertia = round(float(inertia), 6)

    profiles, key_map = build_cluster_profiles(features, scores, labels)
    assignments = []
    for index, feature in enumerate(features):
        assignments.append(
            {
                "member_id": feature["member_id"],
                "member_no": feature["member_no"],
                "cluster_key": key_map[int(labels[index])],
                "r_score": int(scores[index, 0]),
                "f_score": int(scores[index, 1]),
                "m_score": int(scores[index, 2]),
                "recency_days": feature["recency_days"],
                "frequency": feature["frequency"],
                "monetary": feature["monetary"],
            }
        )
    histograms = build_histograms(features, scores)
    scatter = build_scatter(features, labels, key_map)
    gmv_total = round(sum(item["monetary"] for item in features), 2)

    return {
        "as_of": as_of_date.isoformat(),
        "random_state": int(random_state),
        "requested_k": requested_k,
        "selected_k": selected_k,
        "silhouette": round(float(silhouette), 4),
        "inertia": round(float(inertia), 4),
        "silhouette_curve": sweep,
        "member_count": len(features),
        "cluster_count": len(profiles),
        "gmv_total": gmv_total,
        "clusters": profiles,
        "assignments": assignments,
        "histograms": histograms,
        "scatter": scatter,
        "scoring_note": "等频五分位打分（每档约 20%），R 反向；z-score 标准化后进入 KMeans",
    }
