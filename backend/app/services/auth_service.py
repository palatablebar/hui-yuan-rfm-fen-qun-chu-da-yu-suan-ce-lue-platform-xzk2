"""登录与用户上下文。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import AppError, ErrorCode
from app.constants.roles import ROLE_META
from app.models import User
from app.utils.password import verify_password


class AuthServiceError(AppError):
    pass


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AppError(ErrorCode.BAD_CREDENTIALS, "邮箱或密码不正确", 401)
    return user


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def serialize_user(user: User) -> dict:
    meta = ROLE_META.get(user.role, {"label": user.role})
    permissions = []
    if user.role in ("admin", "analyst"):
        permissions.append("segment:run")
    if user.role in ("admin", "analyst"):
        permissions.append("export:create")
    if user.role == "admin":
        permissions.extend(["strategy:write", "strategy:publish", "audit:read"])
    permissions.append("read")
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": meta["label"],
        "permissions": permissions,
    }
