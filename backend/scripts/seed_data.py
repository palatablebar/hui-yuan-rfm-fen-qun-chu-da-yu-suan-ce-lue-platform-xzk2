"""拾光咖啡演示数据集生成器（确定性）。

生成 8 家门店 / 600 名会员 / 2400 条订单事实（订单数由 F 分档精确凑满 2400）。

做法：先给每个会员一个潜在客群的 RFM「偏好值」，按偏好值排序做等频五分位
打分（每个维度恰好 120 人一档），再把分数映射回真实值区间（R 天数、F 订单数、
M 累计金额）。因此：
- 订单事实表中的 R/F/M 聚合值再做五分位打分，会复现同一套分数；
- 分群结果完全由订单 + 算法推导，潜在客群标签不落库；
- 固定 ``RANDOM_SEED``，两次 seed 生成完全一致的数据，分群可复现。

``seed 脚本`` 与 ``离线调参脚本`` 共用本模块。
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta

import numpy as np

RANDOM_SEED = 20261112
REFERENCE_DATE = date(2026, 11, 12)
TARGET_MEMBERS = 600
TARGET_ORDERS = 2400
# 分数 → 订单数：1/2/3/5/9 使总数恰好 2400（600 人 × 4 单均值）
FREQ_BY_SCORE = {1: 1, 2: 2, 3: 3, 4: 5, 5: 9}
# 分数 → 原始值区间（互不重叠，保证五分位可复现）
RECENCY_BANDS = {1: (175, 300), 2: (130, 174), 3: (95, 129), 4: (55, 94), 5: (3, 54)}
MONETARY_BANDS = {
    1: (180.0, 480.0),
    2: (480.0, 950.0),
    3: (950.0, 1700.0),
    4: (1700.0, 3200.0),
    5: (3200.0, 9500.0),
}

STORES = [
    {"code": "SH01", "name": "梧桐里店", "district": "徐汇区", "opened": "2021-04"},
    {"code": "SH02", "name": "滨江店", "district": "浦东新区", "opened": "2021-09"},
    {"code": "SH03", "name": "万象城店", "district": "闵行区", "opened": "2022-03"},
    {"code": "SH04", "name": "大学城店", "district": "杨浦区", "opened": "2022-08"},
    {"code": "SH05", "name": "老城厢店", "district": "黄浦区", "opened": "2023-01"},
    {"code": "SH06", "name": "科创园店", "district": "浦东新区", "opened": "2023-06"},
    {"code": "SH07", "name": "湖畔店", "district": "青浦区", "opened": "2024-02"},
    {"code": "SH08", "name": "机场店", "district": "长宁区", "opened": "2024-10"},
]

# 潜在客群：base = (R 偏好天数, F 偏好单数, M 偏好金额)，jitter = 同尺度扰动。
# 标签不落库，仅供造数与调参；分群结论由算法给出。
GROUPS = [
    {
        "key": "A",
        "count": 78,
        "base": (230.0, 8.0, 7800.0),
        "jitter": (10.0, 0.3, 200.0),
        "consent": 0.86,
        "coupon_use": 0.35,
        "coupon_redeem": 0.22,
        "join": (2023, 1, 2024, 6),
    },
    {
        "key": "B",
        "count": 132,
        "base": (16.0, 7.0, 5200.0),
        "jitter": (16.0, 0.9, 800.0),
        "consent": 0.78,
        "coupon_use": 0.80,
        "coupon_redeem": 0.62,
        "join": (2023, 1, 2024, 9),
    },
    {
        "key": "C",
        "count": 150,
        "base": (26.0, 1.4, 760.0),
        "jitter": (20.0, 0.5, 240.0),
        "consent": 0.90,
        "coupon_use": 0.60,
        "coupon_redeem": 0.44,
        "join": (2026, 3, 2026, 11),
    },
    {
        "key": "D",
        "count": 120,
        "base": (96.0, 2.8, 2100.0),
        "jitter": (22.0, 0.7, 480.0),
        "consent": 0.72,
        "coupon_use": 0.90,
        "coupon_redeem": 0.78,
        "join": (2024, 2, 2025, 8),
    },
    {
        "key": "E",
        "count": 120,
        "base": (165.0, 1.6, 640.0),
        "jitter": (22.0, 0.5, 200.0),
        "consent": 0.65,
        "coupon_use": 0.25,
        "coupon_redeem": 0.14,
        "join": (2023, 1, 2024, 4),
    },
]

# 调参旋钮（默认即验收口径；env 仅用于离线调参，不影响 seed 幂等）
JITTER_SCALE = float(os.environ.get("RFM_JITTER_SCALE", "1.86"))

SURNAMES = list(
    "王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏蒋蔡贾丁魏薛叶余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文"
)
GIVEN = [
    "一鸣", "思远", "雨桐", "子墨", "嘉宁", "文博", "欣然", "若溪", "宇航", "沐辰",
    "安琪", "浩宇", "清妍", "致远", "可欣", "明轩", "语彤", "亦凡", "若谷", "晨曦",
    "佳怡", "睿泽", "婉清", "斯远", "知夏", "慕白", "静姝", "星野", "书瑶", "望舒",
    "景行", "南絮", "一诺", "柏林", "沁禾", "听澜", "照野", "云舒", "锦程", "怀瑾",
]


def _random_join_date(rng: np.random.Generator, span: tuple[int, int, int, int]) -> date:
    start_year, start_month, end_year, end_month = span
    start_index = start_year * 12 + start_month
    end_index = end_year * 12 + end_month
    pick = int(rng.integers(start_index, end_index + 1))
    year, month = divmod(pick, 12)
    if month == 0:
        year -= 1
        month = 12
    return date(year, month, int(rng.integers(1, 28)))


def _rank_scores(preferences: np.ndarray, descending: bool) -> np.ndarray:
    """按偏好排序切成 5 个等频档，返回 1..5 分（每档 120 人）。"""
    n = preferences.size
    order = np.argsort(-preferences if descending else preferences, kind="mergesort")
    scores = np.empty(n, dtype=int)
    scores[order] = (np.arange(n) * 5 // n) + 1
    return scores


def _split_amount(rng: np.random.Generator, target: float, parts: int) -> list[float]:
    weights = 0.35 + rng.random(parts)
    weights = weights / weights.sum()
    amounts = np.round(target * weights, 2)
    amounts[-1] = round(target - float(amounts[:-1].sum()), 2)
    for index in range(parts):
        if amounts[index] < 18.0:
            deficit = 18.0 - float(amounts[index])
            amounts[index] = 18.0
            biggest = int(np.argmax(amounts))
            if biggest != index:
                amounts[biggest] = round(float(amounts[biggest]) - deficit, 2)
    return [float(value) for value in amounts]


def build_demo_dataset() -> dict:
    rng = np.random.default_rng(RANDOM_SEED)
    members: list[dict] = []
    member_index = 0
    for group in GROUPS:
        base_r, base_f, base_m = group["base"]
        jit_r, jit_f, jit_m = group["jitter"]
        for _ in range(group["count"]):
            member_index += 1
            store = STORES[(member_index - 1) % len(STORES)]
            joined_at = _random_join_date(rng, group["join"])
            members.append(
                {
                    "member_no": f"SG-M{member_index:04d}",
                    "name": SURNAMES[(member_index * 7) % len(SURNAMES)]
                    + GIVEN[(member_index * 11) % len(GIVEN)],
                    "phone": f"1{int(rng.integers(3, 9))}{int(rng.integers(0, 10))}****{int(rng.integers(1000, 9999))}",
                    "store_code": store["code"],
                    "store_name": store["name"],
                    "joined_at": joined_at,
                    "consent": bool(rng.random() < group["consent"]),
                    "latent_group": group["key"],
                    "pref_r": base_r + float(rng.normal(0.0, jit_r)) * JITTER_SCALE,
                    "pref_f": base_f + float(rng.normal(0.0, jit_f)) * JITTER_SCALE,
                    "pref_m": base_m + float(rng.normal(0.0, jit_m)) * JITTER_SCALE,
                    "coupon_use": group["coupon_use"],
                    "coupon_redeem": group["coupon_redeem"],
                }
            )

    # --- 等频五分位：每个维度恰好 120 人一档 ---
    pref_r = np.array([item["pref_r"] for item in members])
    pref_f = np.array([item["pref_f"] for item in members])
    pref_m = np.array([item["pref_m"] for item in members])
    score_r = _rank_scores(pref_r, descending=True)  # 天数越大 → R 分越低
    score_f = _rank_scores(pref_f, descending=False)
    score_m = _rank_scores(pref_m, descending=False)

    # --- 分数映射回真实值 ---
    for index, member in enumerate(members):
        r_low, r_high = RECENCY_BANDS[int(score_r[index])]
        m_low, m_high = MONETARY_BANDS[int(score_m[index])]
        member["target_recency"] = int(rng.integers(r_low, r_high + 1))
        member["target_frequency"] = int(FREQ_BY_SCORE[int(score_f[index])])
        member["target_monetary"] = round(float(rng.uniform(m_low, m_high)), 2)

    total_frequency = sum(item["target_frequency"] for item in members)
    if total_frequency != TARGET_ORDERS:  # 防呆：默认口径下必须恰好 2400
        raise RuntimeError(f"frequency design drifted: {total_frequency} != {TARGET_ORDERS}")

    # --- 订单事实 ---
    orders: list[dict] = []
    order_index = 0
    coupon_faces = np.array([8, 12, 15, 20, 25, 30])
    for member in members:
        frequency = member["target_frequency"]
        amounts = _split_amount(rng, float(member["target_monetary"]), frequency)
        last_date = REFERENCE_DATE - timedelta(days=member["target_recency"])
        dates = [last_date]
        cursor_date = last_date
        earliest = member["joined_at"] + timedelta(days=1)
        for _ in range(frequency - 1):
            candidate = cursor_date - timedelta(days=int(rng.integers(3, 70)))
            if candidate <= earliest:
                candidate = earliest + timedelta(days=int(rng.integers(0, 10)))
            cursor_date = candidate
            dates.append(cursor_date)
        dates.sort()
        for slot in range(frequency):
            order_index += 1
            ordered_at = datetime.combine(
                dates[slot],
                time(hour=int(rng.integers(8, 21)), minute=int(rng.integers(0, 60))),
            )
            coupon_issued = bool(rng.random() < member["coupon_use"])
            coupon_redeemed = bool(coupon_issued and (rng.random() < member["coupon_redeem"]))
            coupon_discount = (
                float(coupon_faces[int(rng.integers(0, len(coupon_faces)))])
                if coupon_issued
                else 0.0
            )
            orders.append(
                {
                    "order_no": f"SG-O{order_index:06d}",
                    "member_no": member["member_no"],
                    "store_code": member["store_code"],
                    "amount": round(amounts[slot], 2),
                    "ordered_at": ordered_at,
                    "coupon_issued": coupon_issued,
                    "coupon_redeemed": coupon_redeemed,
                    "coupon_discount": coupon_discount,
                }
            )

    return {"stores": STORES, "members": members, "orders": orders}


if __name__ == "__main__":
    dataset = build_demo_dataset()
    print(
        "stores=%d members=%d orders=%d sum_amount=%.2f"
        % (
            len(dataset["stores"]),
            len(dataset["members"]),
            len(dataset["orders"]),
            sum(item["amount"] for item in dataset["orders"]),
        )
    )
