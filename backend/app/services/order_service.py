"""订单事实聚合：门店订单量 / GMV / 券核销率。

OrderFact 是 RFM 分群的唯一事实来源；本服务只做只读聚合，供 RFM 明细页
展示「订单事实」侧的门店基数与券历史，不参与写操作。
"""
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.models import Member, OrderFact
from app.utils.formatting import ratio


def order_summary(db: Session) -> dict:
    rows = db.execute(
        select(
            OrderFact.store_code,
            Member.store_name,
            func.count(OrderFact.id),
            func.coalesce(func.sum(OrderFact.amount), 0),
            func.coalesce(func.sum(cast(OrderFact.coupon_issued, Integer)), 0),
            func.coalesce(func.sum(cast(OrderFact.coupon_redeemed, Integer)), 0),
        )
        .join(Member, Member.id == OrderFact.member_id)
        .group_by(OrderFact.store_code, Member.store_name)
        .order_by(OrderFact.store_code)
    ).all()

    stores = []
    totals = {"orders": 0, "gmv": 0.0, "coupon_issued": 0, "coupon_redeemed": 0}
    for store_code, store_name, orders, gmv, issued, redeemed in rows:
        orders = int(orders)
        gmv = float(gmv or 0)
        issued = int(issued or 0)
        redeemed = int(redeemed or 0)
        stores.append(
            {
                "store_code": store_code,
                "store_name": store_name,
                "orders": orders,
                "gmv": round(gmv, 2),
                "coupon_issued": issued,
                "coupon_redeemed": redeemed,
                "redemption_rate": ratio(redeemed, issued),
            }
        )
        totals["orders"] += orders
        totals["gmv"] += gmv
        totals["coupon_issued"] += issued
        totals["coupon_redeemed"] += redeemed

    totals["gmv"] = round(totals["gmv"], 2)
    totals["redemption_rate"] = ratio(totals["coupon_redeemed"], totals["coupon_issued"])
    return {"totals": totals, "stores": stores}
