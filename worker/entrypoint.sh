#!/usr/bin/env bash
# 等 PostgreSQL + Redis，写心跳文件，再起 Celery worker。
set -euo pipefail

echo "[worker] waiting for db/redis ..."
python /app/worker/wait_for_deps.py

# compose healthcheck 读取的心跳文件
( while true; do date +%s > /tmp/rfmseg-worker-heartbeat; sleep 5; done ) &

exec celery -A app.config.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --hostname=rfmseg-worker@%h \
  --without-gossip --without-mingle --without-heartbeat
