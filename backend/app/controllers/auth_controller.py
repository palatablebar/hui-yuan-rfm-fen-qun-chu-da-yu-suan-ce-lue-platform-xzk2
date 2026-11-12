"""登录 / 当前用户。"""
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import LoginRequest
from app.services import auth_service
from app.utils.jwt import create_access_token


def login(db: Session, payload: LoginRequest) -> dict:
    user = auth_service.authenticate(db, payload.email, payload.password)
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "expires_in_hours": 8,
        "user": auth_service.serialize_user(user),
    }


def me(user: User) -> dict:
    return {"user": auth_service.serialize_user(user)}
