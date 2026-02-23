import asyncio
from uuid import UUID

import structlog
import structlog.contextvars
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

from app.core.database import async_session_factory
from app.middleware.tenant_context import set_tenant_context
from app.models.listing import Listing
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.workers.tasks.media_process.download_listing_photos",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    soft_time_limit=180,
    time_limit=240,
)
def download_listing_photos(self, tenant_id: str, listing_id: str, photo_urls: list[dict], correlation_id: str | None = None):
    """Download and store listing photos from MLS."""
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        asyncio.run(_download_photos(tenant_id, listing_id, photo_urls))
    except SoftTimeLimitExceeded:
        logger.error(
            "photo_download_timeout",
            tenant_id=tenant_id,
            listing_id=listing_id,
        )
        raise
    except Exception as exc:
        logger.error(
            "photo_download_error",
            tenant_id=tenant_id,
            listing_id=listing_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


async def _download_photos(tenant_id: str, listing_id: str, photo_urls: list[dict]):
    from app.services.media_service import MediaService

    media_service = MediaService()
    stored = []

    for photo in photo_urls:
        try:
            url = photo.get("url")
            if not url:
                continue

            result = await media_service.download_from_url(
                url=url,
                tenant_id=tenant_id,
                filename=f"listing-{listing_id}-{photo.get('order', 0)}.jpg",
            )
            stored.append(result)

        except Exception as e:
            await logger.aerror(
                "photo_download_error",
                listing_id=listing_id,
                url=photo.get("url"),
                error=str(e),
            )

    # Update the listing's photos JSONB field with stored S3 URLs
    if stored:
        async with async_session_factory() as db:
            await set_tenant_context(db, tenant_id)
            result = await db.execute(
                select(Listing).where(
                    Listing.id == UUID(listing_id),
                    Listing.tenant_id == UUID(tenant_id),
                )
            )
            listing = result.scalar_one_or_none()
            if listing:
                listing.photos = stored
                db.add(listing)
                await db.commit()

    await logger.ainfo(
        "photos_downloaded",
        listing_id=listing_id,
        total=len(photo_urls),
        stored=len(stored),
    )
