from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.content_version import ContentVersion
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent


class ContentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        tenant_id: UUID,
        listing_id: UUID,
        user_id: UUID,
        content_type: str,
        tone: str,
        body: str,
        metadata: dict,
        ai_model: str,
        prompt_tokens: int,
        completion_tokens: int,
        generation_time_ms: int,
        brand_profile_id: UUID | None = None,
    ) -> Content:
        content = Content(
            tenant_id=tenant_id,
            listing_id=listing_id,
            user_id=user_id,
            brand_profile_id=brand_profile_id,
            content_type=content_type,
            tone=tone,
            body=body,
            content_metadata=metadata,
            ai_model=ai_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            generation_time_ms=generation_time_ms,
        )
        self.db.add(content)
        await self.db.flush()

        # Save initial version
        version = ContentVersion(
            content_id=content.id,
            version=1,
            body=body,
            content_metadata=metadata,
        )
        self.db.add(version)

        return content

    async def track_usage(
        self,
        tenant_id: UUID,
        user_id: UUID,
        content_type: str,
        count: int,
        tokens: int,
    ) -> None:
        event = UsageEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="content_generation",
            content_type=content_type,
            tokens_used=tokens,
            credits_consumed=count,
        )
        self.db.add(event)

    async def get_remaining_credits(self, tenant_id: UUID) -> int:
        # Get tenant's limit
        result = await self.db.execute(
            select(Tenant.monthly_generation_limit).where(Tenant.id == tenant_id)
        )
        limit = result.scalar()
        if limit is None:
            limit = 50

        # Get current month's usage
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        usage_result = await self.db.execute(
            select(func.coalesce(func.sum(UsageEvent.credits_consumed), 0)).where(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.event_type == "content_generation",
                UsageEvent.created_at >= month_start,
            )
        )
        used = usage_result.scalar()

        return max(0, limit - used)
