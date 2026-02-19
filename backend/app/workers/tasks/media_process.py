import asyncio

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.media_process.download_listing_photos")
def download_listing_photos(tenant_id: str, listing_id: str, photo_urls: list[dict]):
    """Download and store listing photos from MLS."""
    asyncio.run(_download_photos(tenant_id, listing_id, photo_urls))


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

    await logger.ainfo(
        "photos_downloaded",
        listing_id=listing_id,
        total=len(photo_urls),
        stored=len(stored),
    )
