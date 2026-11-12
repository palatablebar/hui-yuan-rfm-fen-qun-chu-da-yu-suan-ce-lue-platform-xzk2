from datetime import date

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    k: int | str | None = Field(default="auto")
    as_of: date | None = None
    name: str | None = Field(default=None, max_length=80)
