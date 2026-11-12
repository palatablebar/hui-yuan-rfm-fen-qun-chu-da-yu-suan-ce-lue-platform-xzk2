"""Bearer Token 中间件 + 当前用户/角色依赖。

Token 只用于识别身份；每次请求都从 PostgreSQL 重新读取 users.role，
数据库是权限的唯一权威来源（低权角色真的会拿到 403）。
"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config.database import get_db
from app.constants.error_codes import AppError, ErrorCode, forbidden, unauthorized
from app.models import User
from app.schemas.common import error_envelope
from app.utils.jwt import TokenError, decode_access_token

PUBLIC_PATHS = {
    "/health",
    "/api/health",
    "/auth/login",
    "/api/auth/login",
    "/meta/enums",
    "/api/meta/enums",
    "/openapi.json",
    "/docs",
    "/redoc",
}
PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi.json")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user_claims = None
        header = request.headers.get("authorization") or ""
        if header.lower().startswith("bearer "):
            try:
                request.state.user_claims = decode_access_token(header[7:].strip())
            except TokenError:
                request.state.user_claims = None
        path = request.url.path.rstrip("/") or "/"
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.state.user_claims is None:
            return JSONResponse(
                status_code=401,
                content=error_envelope(
                    ErrorCode.UNAUTHORIZED,
                    "未登录或登录已过期",
                    getattr(request.state, "request_id", None),
                ),
            )
        return await call_next(request)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    claims = getattr(request.state, "user_claims", None)
    if not claims or not claims.get("sub"):
        raise unauthorized()
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise unauthorized()
    return user


def require_roles(*roles: str):
    """角色依赖：不满足时抛 403（真实 HTTP 403，非前端隐藏）。"""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden(f"角色 {user.role} 无权访问该接口（需要：{'/'.join(roles)}）")
        return user

    return dependency


def ensure_roles(user: User, *roles: str) -> None:
    if user.role not in roles:
        raise AppError(ErrorCode.FORBIDDEN, f"角色 {user.role} 无权执行该操作", 403)
