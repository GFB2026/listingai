from uuid import UUID

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.brand_profile import BrandProfile
from app.models.listing import Listing
from app.services.prompt_builder import PromptBuilder

# Model selection based on content type
MODEL_MAP = {
    "listing_description": "claude-sonnet-4-5-20250929",
    "social_instagram": "claude-sonnet-4-5-20250929",
    "social_facebook": "claude-sonnet-4-5-20250929",
    "social_linkedin": "claude-sonnet-4-5-20250929",
    "social_x": "claude-haiku-4-5-20251001",
    "email_just_listed": "claude-sonnet-4-5-20250929",
    "email_open_house": "claude-sonnet-4-5-20250929",
    "email_drip": "claude-sonnet-4-5-20250929",
    "flyer": "claude-sonnet-4-5-20250929",
    "video_script": "claude-sonnet-4-5-20250929",
}


class AIService:
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.prompt_builder = PromptBuilder()

    async def generate(
        self,
        listing: Listing,
        content_type: str,
        tone: str,
        brand_profile_id: str | None,
        instructions: str | None,
        tenant_id: str,
        db: AsyncSession,
    ) -> dict:
        # Load brand profile if specified
        brand_profile = None
        if brand_profile_id:
            result = await db.execute(
                select(BrandProfile).where(
                    BrandProfile.id == UUID(brand_profile_id),
                    BrandProfile.tenant_id == UUID(tenant_id),
                )
            )
            brand_profile = result.scalar_one_or_none()
        else:
            # Try to get default brand profile
            result = await db.execute(
                select(BrandProfile).where(
                    BrandProfile.tenant_id == UUID(tenant_id),
                    BrandProfile.is_default == True,
                )
            )
            brand_profile = result.scalar_one_or_none()

        # Build prompt using three-layer architecture
        system_prompt, user_prompt = self.prompt_builder.build(
            listing=listing,
            content_type=content_type,
            tone=tone,
            brand_profile=brand_profile,
            instructions=instructions,
        )

        # Select model
        model = MODEL_MAP.get(content_type, "claude-sonnet-4-5-20250929")

        # Call Claude API
        response = await self.client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        body = response.content[0].text
        metadata = self._extract_metadata(body, content_type)

        return {
            "body": body,
            "metadata": metadata,
            "model": model,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
        }

    def _extract_metadata(self, body: str, content_type: str) -> dict:
        metadata = {
            "word_count": len(body.split()),
            "character_count": len(body),
        }

        # Extract hashtags for social media content
        if content_type.startswith("social_"):
            hashtags = [word for word in body.split() if word.startswith("#")]
            metadata["hashtags"] = hashtags

        return metadata
