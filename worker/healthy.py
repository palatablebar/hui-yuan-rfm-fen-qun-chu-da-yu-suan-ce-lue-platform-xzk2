"""Compose healthcheck：读取 worker 每 5 秒刷新的心跳文件，超过 60 秒视为不健康。"""
import os
import sys
import time

HEARTBEAT = "/tmp/rfmseg-worker-heartbeat"
MAX_AGE_SECONDS = 60


def main() -> int:
    try:
        age = time.time() - os.path.getmtime(HEARTBEAT)
    except OSError:
        print(f"heartbeat file {HEARTBEAT} missing")
        return 1
    if age > MAX_AGE_SECONDS:
        print(f"heartbeat stale: {age:.1f}s > {MAX_AGE_SECONDS}s")
        return 1
    print(f"worker healthy: heartbeat age {age:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
