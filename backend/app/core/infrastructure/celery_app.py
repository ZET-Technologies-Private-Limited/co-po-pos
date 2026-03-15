"""
Celery application for async background workloads.
"""
from __future__ import annotations

from celery import Celery

from app.core.config.settings import get_settings

settings = get_settings()

broker_url = settings.celery_broker_url or settings.redis_url or "redis://localhost:6379/0"
result_backend = settings.celery_result_backend or settings.redis_url or "redis://localhost:6379/0"

celery_app = Celery(
    "obe_backend",
    broker=broker_url,
    backend=result_backend,
    include=["app.modules.attainment_engine.tasks.attainment_tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
