from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    role_label: str
    permissions: list[str]
