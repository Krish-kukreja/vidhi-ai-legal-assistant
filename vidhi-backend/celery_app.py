"""
Celery Application Configuration for VIDHI
Handles background task processing for long-running operations
"""

import os
from celery import Celery
from celery.schedules import crontab

# Get Redis URL from environment
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Create Celery app
celery_app = Celery(
    "vidhi",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=[
        "tasks.data_pipeline_tasks",
        "tasks.document_tasks",
        "tasks.audio_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes hard limit
    task_soft_time_limit=1500,  # 25 minutes soft limit
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=86400,  # 24 hours
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    
    # Retry settings
    task_default_retry_delay=2,  # 2 seconds
    task_max_retries=3,
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        "refresh-data-pipeline-daily": {
            "task": "tasks.data_pipeline_tasks.refresh_data_pipeline",
            "schedule": crontab(hour=2, minute=0),  # 2 AM daily
        },
        "cleanup-old-tasks": {
            "task": "tasks.data_pipeline_tasks.cleanup_old_tasks",
            "schedule": crontab(hour=3, minute=0),  # 3 AM daily
        },
    },
)

# Task routes (optional - for task prioritization)
celery_app.conf.task_routes = {
    "tasks.data_pipeline_tasks.*": {"queue": "data_pipeline"},
    "tasks.document_tasks.*": {"queue": "documents"},
    "tasks.audio_tasks.*": {"queue": "audio"},
}

if __name__ == "__main__":
    celery_app.start()
