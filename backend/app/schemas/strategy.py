from pydantic import BaseModel, Field


class StrategyCreateRequest(BaseModel):
    run_id: int
    name: str | None = Field(default=None, max_length=90)
    total_budget: float = Field(default=8000)


class ExportCreateRequest(BaseModel):
    cluster_key: str = Field(min_length=2, max_length=8)
    channel: str = Field(default="企微", max_length=20)
    note: str | None = Field(default=None, max_length=200)
    # 前端为每次「导出动作」生成稳定幂等键（刷新/重试保持不变），
    # 服务端同时按 (策略, 簇, 渠道) 自然键去重，双保险防止重复名单与预算占用。
    idempotency_key: str | None = Field(default=None, max_length=80)


class PublishRequest(BaseModel):
    note: str | None = Field(default=None, max_length=200)
