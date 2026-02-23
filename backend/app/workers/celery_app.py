import structlog
from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure

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
    result_expires=3600,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_reject_on_worker_lost=True,
    # Graceful shutdown — restart workers to prevent memory leaks
    worker_max_tasks_per_child=200,
    worker_max_memory_per_child=512_000,  # 512 MB
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "sync-mls-listings": {
        "task": "app.workers.tasks.mls_sync.sync_all_tenants",
        "schedule": crontab(minute=f"*/{settings.mls_sync_interval_minutes}"),
    },
}


@task_failure.connect
def handle_task_permanent_failure(sender=None, task_id=None, exception=None,
                                  args=None, kwargs=None, traceback=None,
                                  einfo=None, **kw):
    """Log tasks that have exhausted all retries for post-mortem investigation."""
    logger = structlog.get_logger()
    logger.error(
        "task_permanently_failed",
        task_name=sender.name if sender else "unknown",
        task_id=task_id,
        args=args,
        kwargs=kwargs,
        error=str(exception),
    )
