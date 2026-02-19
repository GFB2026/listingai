import asyncio

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.mls_sync.sync_mls_listings")
def sync_mls_listings(tenant_id: str):
    """Sync MLS listings for a specific tenant."""
    asyncio.run(_sync_tenant(tenant_id))


@celery_app.task(name="app.workers.tasks.mls_sync.sync_all_tenants")
def sync_all_tenants():
    """Periodic task: sync all tenants with enabled MLS connections."""
    asyncio.run(_sync_all())


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
