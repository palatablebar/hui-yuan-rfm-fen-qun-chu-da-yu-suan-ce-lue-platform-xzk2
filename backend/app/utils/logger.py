"""结构化单行日志，便于 docker logs / QA 脚本 grep。"""
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(message)s",
)
_logger = logging.getLogger("rfmseg")


def log_event(event: str, **fields) -> None:
    payload = {"event": event, **fields}
    _logger.info(json.dumps(payload, ensure_ascii=False, default=str))
