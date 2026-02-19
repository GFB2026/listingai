from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "listingai",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.mls_sync",
        "app.workers.tasks.content_batch",
        "app.workers.tasks.media_process",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "sync-mls-listings": {
        "task": "app.workers.tasks.mls_sync.sync_all_tenants",
        "schedule": crontab(minute=f"*/{settings.mls_sync_interval_minutes}"),
    },
}
