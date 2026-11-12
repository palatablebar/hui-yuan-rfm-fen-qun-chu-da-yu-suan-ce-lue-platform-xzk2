"""worker 启动前等待 PostgreSQL / Redis 就绪。"""
import sys
import time

from redis import Redis
from sqlalchemy import create_engine, text

from app.config.settings import settings

for attempt in range(60):
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Redis.from_url(settings.REDIS_URL, socket_timeout=1).ping()
        print("[worker] db and redis are ready")
        sys.exit(0)
    except Exception as exc:  # pragma: no cover - 基础设施重试
        if attempt % 5 == 0:
            print(f"[worker] not ready ({type(exc).__name__}); retrying", flush=True)
        time.sleep(3)
print("[worker] dependencies never became ready", flush=True)
sys.exit(1)
