"""
Celery Configuration and Task Definitions
Implements all async tasks from specification
"""
from celery import Celery
from celery.schedules import crontab
from kombu import Queue
import os
from app.core.config.settings import get_settings

settings = get_settings()

# Celery app configuration
celery_app = Celery(
    "obe_tasks",
    broker=getattr(settings, 'redis_url', 'redis://localhost:6379/1'),
    backend=getattr(settings, 'redis_url', 'redis://localhost:6379/1'),
    include=[
        'app.core.infrastructure.celery_tasks'
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        'app.core.infrastructure.celery_tasks.parse_marks_excel': {'queue': 'marks_processing'},
        'app.core.infrastructure.celery_tasks.compute_co_attainment': {'queue': 'attainment'},
        'app.core.infrastructure.celery_tasks.generate_pdf_report': {'queue': 'reports'},
        'app.core.infrastructure.celery_tasks.generate_excel_report': {'queue': 'reports'},
        'app.core.infrastructure.celery_tasks.send_email_notification': {'queue': 'notifications'},
    },
    
    # Queue definitions
    task_default_queue='default',
    task_queues=(
        Queue('default'),
        Queue('marks_processing'),
        Queue('attainment'),
        Queue('reports'),
        Queue('notifications'),
        Queue('maintenance'),
    ),
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'nightly-integrity-check': {
            'task': 'app.core.infrastructure.celery_tasks.nightly_integrity_check',
            'schedule': crontab(hour=2, minute=0),  # 02:00 daily
        },
        'remind-marks-deadline': {
            'task': 'app.core.infrastructure.celery_tasks.remind_marks_deadline',
            'schedule': crontab(hour=9, minute=0),  # 09:00 daily
        },
        'cleanup-expired-cache': {
            'task': 'app.core.infrastructure.celery_tasks.cleanup_expired_cache',
            'schedule': crontab(hour=3, minute=0),  # 03:00 daily
        },
    },
)

if __name__ == '__main__':
    celery_app.start()