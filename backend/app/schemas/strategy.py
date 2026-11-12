from pydantic import BaseModel, Field


class StrategyCreateRequest(BaseModel):
    run_id: int
    name: str | None = Field(default=None, max_length=90)
    total_budget: float = Field(default=8000)


class ExportCreateRequest(BaseModel):
    cluster_key: str = Field(min_length=2, max_length=8)
    channel: str = Field(default="企微", max_length=20)
    note: str | None = Field(default=None, max_length=200)


class PublishRequest(BaseModel):
    note: str | None = Field(default=None, max_length=200)
