"""rfmseg API 入口。

中间件顺序（外→内）：CORS → RequestId → Auth → RateLimit → Audit → 路由 → 错误处理。
同一组路由同时挂在 "" 与 "/api" 下：Nginx 把 /api/ 前缀转发给 backend:8000/，
直接访问 :19247/api/... 也能工作，两种入口行为一致。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import init_db
from app.config.settings import settings
from app.middlewares.audit_logger import AuditMiddleware
from app.middlewares.auth import AuthMiddleware
from app.middlewares.error_handler import RequestIdMiddleware, install_error_handlers
from app.middlewares.rate_limit import RateLimitMiddleware
from app.routes import audit, auth, health, member, meta, order, segment, strategy
from app.utils.logger import log_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.SEED_DEMO:
        try:
            from scripts.seed_demo import run_seed

            result = run_seed()
            log_event("SEED_DEMO_FINISHED", **result)
        except Exception as exc:  # seed 失败只记日志，不阻塞启动
            log_event("SEED_DEMO_FAILED", error=f"{type(exc).__name__}: {exc}")
    yield


app = FastAPI(
    title="rfmseg API",
    description="拾光咖啡 · 会员 RFM 分群与触达预算策略台",
    version="1.0.0",
    lifespan=lifespan,
)

install_error_handlers(app)

app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Row-Count"],
)

for _prefix in ("", "/api"):
    app.include_router(health.router, prefix=_prefix)
    app.include_router(meta.router, prefix=_prefix)
    app.include_router(auth.router, prefix=_prefix)
    app.include_router(member.router, prefix=_prefix)
    app.include_router(order.router, prefix=_prefix)
    app.include_router(segment.router, prefix=_prefix)
    app.include_router(strategy.router, prefix=_prefix)
    app.include_router(audit.router, prefix=_prefix)


@app.get("/")
def index() -> dict:
    return {
        "service": "rfmseg-backend",
        "brand": "拾光咖啡 · 会员运营",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/auth/login",
            "/meta/enums",
            "/members",
            "/segments/runs",
            "/strategies",
            "/audit/logs",
        ],
    }
