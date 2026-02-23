import asyncio

import structlog
import structlog.contextvars
from celery.exceptions import SoftTimeLimitExceeded

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.workers.tasks.mls_sync.sync_mls_listings",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=360,
)
def sync_mls_listings(self, tenant_id: str, correlation_id: str | None = None):
    """Sync MLS listings for a specific tenant."""
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        asyncio.run(_sync_tenant(tenant_id))
    except SoftTimeLimitExceeded:
        logger.error("sync_mls_timeout", tenant_id=tenant_id)
        raise
    except Exception as exc:
        logger.error("sync_mls_error", tenant_id=tenant_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.mls_sync.sync_all_tenants",
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=900,
    retry_jitter=True,
    soft_time_limit=1200,
    time_limit=1500,
)
def sync_all_tenants(self, correlation_id: str | None = None):
    """Periodic task: sync all tenants with enabled MLS connections."""
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        asyncio.run(_sync_all())
    except SoftTimeLimitExceeded:
        logger.error("sync_all_timeout")
        raise
    except Exception as exc:
        logger.error("sync_all_error", error=str(exc))
        raise self.retry(exc=exc)


async def _sync_tenant(tenant_id: str):
    from app.core.database import async_session_factory
    from app.integrations.mls.sync_engine import SyncEngine

    async with async_session_factory() as session:
        engine = SyncEngine(session)
        results = await engine.sync_tenant(tenant_id)
        await session.commit()
        await logger.ainfo("tenant_sync_complete", tenant_id=tenant_id, results=results)


async def _sync_all():
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.integrations.mls.sync_engine import SyncEngine
    from app.models.mls_connection import MLSConnection

    async with async_session_factory() as session:
        result = await session.execute(
            select(MLSConnection.tenant_id)
            .where(MLSConnection.sync_enabled == True)
            .distinct()
        )
        tenant_ids = [str(row[0]) for row in result.all()]

    for tenant_id in tenant_ids:
        try:
            await _sync_tenant(tenant_id)
        except Exception as e:
            await logger.aerror("sync_tenant_error", tenant_id=tenant_id, error=str(e))
