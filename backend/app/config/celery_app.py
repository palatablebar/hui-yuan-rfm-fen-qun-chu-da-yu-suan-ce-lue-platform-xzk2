"""Celery 应用：backend 生产任务，worker 消费任务。"""
from celery import Celery

from app.config.settings import settings

celery_app = Celery(
    "rfmseg",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.segment_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
    task_acks_late=False,
)

app = celery_app
celery = celery_app
