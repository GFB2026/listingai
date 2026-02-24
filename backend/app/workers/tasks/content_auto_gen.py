import asyncio

import structlog
import structlog.contextvars
from celery.exceptions import SoftTimeLimitExceeded

from app.workers.celery_app import celery_app

logger = structlog.get_logger()

# Content types to auto-generate for new listings
AUTO_GEN_CONTENT_TYPES = [
    "listing_description",
    "social_instagram",
    "social_facebook",
    "social_linkedin",
    "social_x",
    "email_just_listed",
    "flyer",
]


@celery_app.task(
    bind=True,
    name="app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=900,
    retry_jitter=True,
    soft_time_limit=600,
    time_limit=720,
)
def auto_generate_for_new_listings(
    self,
    tenant_id: str,
    listing_ids: list[str],
    correlation_id: str | None = None,
):
    """Auto-generate all marketing content for newly detected listings."""
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        asyncio.run(_auto_generate(tenant_id, listing_ids))
    except SoftTimeLimitExceeded:
        logger.error(
            "auto_gen_timeout",
            tenant_id=tenant_id,
            listing_count=len(listing_ids),
        )
        raise
    except Exception as exc:
        logger.error("auto_gen_error", tenant_id=tenant_id, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _auto_generate(tenant_id: str, listing_ids: list[str]):
    import time
    from uuid import UUID

    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.middleware.tenant_context import set_tenant_context
    from app.models.brand_profile import BrandProfile
    from app.models.listing import Listing
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.services.ai_service import AIService
    from app.services.content_service import ContentService

    ai_service = AIService()
    tid = UUID(tenant_id)

    async with async_session_factory() as session:
        await set_tenant_context(session, tenant_id)

        # Load tenant settings to check if auto-gen is enabled
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.id == tid)
        )
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            await logger.aerror("auto_gen_tenant_not_found", tenant_id=tenant_id)
            return

        settings = tenant.settings or {}
        if not settings.get("auto_generate_on_new_listing", True):
            await logger.ainfo("auto_gen_disabled", tenant_id=tenant_id)
            return

        # Determine which content types to generate
        content_types = settings.get(
            "auto_generate_content_types", AUTO_GEN_CONTENT_TYPES
        )
        tone = settings.get("auto_generate_tone", "professional")

        # Get default brand profile
        bp_result = await session.execute(
            select(BrandProfile).where(
                BrandProfile.tenant_id == tid,
                BrandProfile.is_default.is_(True),
            )
        )
        brand_profile = bp_result.scalar_one_or_none()
        brand_profile_id = str(brand_profile.id) if brand_profile else None

        # Get first admin/owner user as the system user for auto-gen
        user_result = await session.execute(
            select(User).where(
                User.tenant_id == tid,
                User.role.in_(["owner", "admin"]),
            ).limit(1)
        )
        system_user = user_result.scalar_one_or_none()
        if not system_user:
            await logger.aerror("auto_gen_no_system_user", tenant_id=tenant_id)
            return

        content_service = ContentService(session)
        generated = 0
        errors = 0

        for listing_id in listing_ids:
            result = await session.execute(
                select(Listing).where(
                    Listing.id == UUID(listing_id),
                    Listing.tenant_id == tid,
                )
            )
            listing = result.scalar_one_or_none()
            if not listing:
                await logger.awarning(
                    "auto_gen_listing_not_found", listing_id=listing_id
                )
                continue

            for content_type in content_types:
                try:
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
                        tenant_id=tid,
                        listing_id=listing.id,
                        user_id=system_user.id,
                        content_type=content_type,
                        tone=tone,
                        brand_profile_id=(
                            UUID(brand_profile_id) if brand_profile_id else None
                        ),
                        body=ai_result["body"],
                        metadata=ai_result.get("metadata", {}),
                        ai_model=ai_result["model"],
                        prompt_tokens=ai_result.get("prompt_tokens", 0),
                        completion_tokens=ai_result.get("completion_tokens", 0),
                        generation_time_ms=generation_time_ms,
                    )
                    generated += 1

                except Exception as e:
                    errors += 1
                    await logger.aerror(
                        "auto_gen_item_error",
                        listing_id=listing_id,
                        content_type=content_type,
                        error=str(e),
                    )

        await session.commit()

    await logger.ainfo(
        "auto_gen_complete",
        tenant_id=tenant_id,
        listing_count=len(listing_ids),
        generated=generated,
        errors=errors,
    )
