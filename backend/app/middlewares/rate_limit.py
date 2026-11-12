"""进程内滑动窗口限流（每用户/每 IP，仅对写操作）。

单实例部署足够；多实例时应换 Redis 实现（README 已注明）。
"""
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config.settings import settings
from app.constants.error_codes import ErrorCode
from app.schemas.common import error_envelope

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    async def dispatch(self, request, call_next):
        if request.method not in _WRITE_METHODS:
            return await call_next(request)
        claims = getattr(request.state, "user_claims", None) or {}
        identity = f"user:{claims.get('sub')}" if claims.get("sub") else f"ip:{request.client.host if request.client else 'unknown'}"
        now = time.monotonic()
        window = settings.RATE_WINDOW_SECONDS
        with self._lock:
            hits = [stamp for stamp in self._hits.get(identity, []) if now - stamp < window]
            if len(hits) >= settings.RATE_WINDOW_MAX:
                self._hits[identity] = hits
                return JSONResponse(
                    status_code=429,
                    content=error_envelope(
                        ErrorCode.RATE_LIMITED,
                        f"{window} 秒内写操作超过 {settings.RATE_WINDOW_MAX} 次，请稍后再试",
                        getattr(request.state, "request_id", None),
                    ),
                )
            hits.append(now)
            self._hits[identity] = hits
        return await call_next(request)
