import asyncio

import structlog
import structlog.contextvars
from celery.exceptions import SoftTimeLimitExceeded

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.workers.tasks.content_batch.batch_generate_content",
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=600,
    time_limit=720,
)
def batch_generate_content(
    self,
    tenant_id: str,
    user_id: str,
    listing_ids: list[str],
    content_type: str,
    tone: str = "professional",
    brand_profile_id: str | None = None,
    correlation_id: str | None = None,
):
    """Batch generate content for multiple listings."""
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        asyncio.run(
            _batch_generate(tenant_id, user_id, listing_ids, content_type, tone, brand_profile_id)
        )
    except SoftTimeLimitExceeded:
        logger.error(
            "batch_generate_timeout",
            tenant_id=tenant_id,
            listing_count=len(listing_ids),
        )
        raise
    except Exception as exc:
        logger.error("batch_generate_error", tenant_id=tenant_id, error=str(exc))
        raise self.retry(exc=exc)


async def _batch_generate(
    tenant_id: str,
    user_id: str,
    listing_ids: list[str],
    content_type: str,
    tone: str,
    brand_profile_id: str | None,
):
    import time
    from uuid import UUID

    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.middleware.tenant_context import set_tenant_context
    from app.models.listing import Listing
    from app.services.ai_service import AIService
    from app.services.content_service import ContentService

    ai_service = AIService()

    async with async_session_factory() as session:
        await set_tenant_context(session, tenant_id)

        content_service = ContentService(session)

        for listing_id in listing_ids:
            try:
                result = await session.execute(
                    select(Listing).where(
                        Listing.id == UUID(listing_id),
                        Listing.tenant_id == UUID(tenant_id),
                    )
                )
                listing = result.scalar_one_or_none()
                if not listing:
                    await logger.awarning("listing_not_found", listing_id=listing_id)
                    continue

                start = time.time()
                ai_result = await ai_service.generate(
                    listing=listing,
                    content_type=content_type,
                    tone=tone,
                    brand_profile_id=brand_profile_id,
                    instructions=None,
                    tenant_id=tenant_id,
                    db=session,
                )
                generation_time_ms = int((time.time() - start) * 1000)

                await content_service.create(
                    tenant_id=UUID(tenant_id),
                    listing_id=listing.id,
                    user_id=UUID(user_id),
                    content_type=content_type,
                    tone=tone,
                    brand_profile_id=UUID(brand_profile_id) if brand_profile_id else None,
                    body=ai_result["body"],
                    metadata=ai_result.get("metadata", {}),
                    ai_model=ai_result["model"],
                    prompt_tokens=ai_result.get("prompt_tokens", 0),
                    completion_tokens=ai_result.get("completion_tokens", 0),
                    generation_time_ms=generation_time_ms,
                )

                await logger.ainfo("batch_item_complete", listing_id=listing_id)

            except Exception as e:
                await logger.aerror(
                    "batch_item_error", listing_id=listing_id, error=str(e)
                )

        await session.commit()

    await logger.ainfo(
        "batch_complete",
        tenant_id=tenant_id,
        listing_count=len(listing_ids),
        content_type=content_type,
    )
