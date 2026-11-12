from pydantic import BaseModel


class OrderStoreStat(BaseModel):
    store_code: str
    store_name: str
    orders: int
    gmv: float
    coupon_issued: int
    coupon_redeemed: int
    redemption_rate: float


class OrderSummary(BaseModel):
    totals: dict
    stores: list[OrderStoreStat]
