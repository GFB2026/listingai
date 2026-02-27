from app.models.brand_profile import BrandProfile
from app.models.listing import Listing
from app.services.market_data import build_market_section
from app.prompts.email_campaign import (
    EMAIL_DRIP_SYSTEM,
    EMAIL_JUST_LISTED_SYSTEM,
    EMAIL_OPEN_HOUSE_SYSTEM,
)
from app.prompts.events import (
    JUST_SOLD_SYSTEM,
    OPEN_HOUSE_INVITE_SYSTEM,
    PRICE_REDUCTION_SYSTEM,
)
from app.prompts.flyer_copy import FLYER_SYSTEM
from app.prompts.listing_description import LISTING_DESCRIPTION_SYSTEM
from app.prompts.social_media import (
    SOCIAL_FACEBOOK_SYSTEM,
    SOCIAL_INSTAGRAM_SYSTEM,
    SOCIAL_LINKEDIN_SYSTEM,
    SOCIAL_X_SYSTEM,
)
from app.prompts.video_script import VIDEO_SCRIPT_SYSTEM

SYSTEM_PROMPTS = {
    "listing_description": LISTING_DESCRIPTION_SYSTEM,
    "social_instagram": SOCIAL_INSTAGRAM_SYSTEM,
    "social_facebook": SOCIAL_FACEBOOK_SYSTEM,
    "social_linkedin": SOCIAL_LINKEDIN_SYSTEM,
    "social_x": SOCIAL_X_SYSTEM,
    "email_just_listed": EMAIL_JUST_LISTED_SYSTEM,
    "email_open_house": EMAIL_OPEN_HOUSE_SYSTEM,
    "email_drip": EMAIL_DRIP_SYSTEM,
    "flyer": FLYER_SYSTEM,
    "video_script": VIDEO_SCRIPT_SYSTEM,
    # Event-specific content types (ported from gor-marketing)
    "open_house_invite": OPEN_HOUSE_INVITE_SYSTEM,
    "price_reduction": PRICE_REDUCTION_SYSTEM,
    "just_sold": JUST_SOLD_SYSTEM,
}


class PromptBuilder:
    """Three-layer prompt assembly: System + Brand Voice + Listing Data."""

    def build(
        self,
        listing: Listing,
        content_type: str,
        tone: str,
        brand_profile: BrandProfile | None = None,
        instructions: str | None = None,
        event_details: str = "",
        market_areas: list[dict] | None = None,
    ) -> tuple[str, str]:
        # Layer 1: System prompt (per content type)
        system = SYSTEM_PROMPTS.get(content_type, LISTING_DESCRIPTION_SYSTEM)
        system = system.replace("{tone}", tone)
        system = system.replace("{event_details}", event_details)

        # Layer 2: Brand voice injection
        if brand_profile:
            brand_section = self._build_brand_section(brand_profile)
            system += f"\n\n{brand_section}"

        # Layer 3: Listing data + user instructions
        user_prompt = self._build_listing_section(listing)

        # Layer 4: Market data enrichment
        if market_areas:
            listing_dict = {
                "address_city": getattr(listing, "address_city", None),
                "address_zip": getattr(listing, "address_zip", None),
                "county": getattr(listing, "county", None),
            }
            market_section = build_market_section(listing_dict, market_areas)
            if market_section:
                user_prompt += f"\n\n{market_section}"

        if instructions:
            user_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{instructions}"

        user_prompt += "\n\nGenerate the content now."

        return system, user_prompt

    def _build_brand_section(self, profile: BrandProfile) -> str:
        parts = ["BRAND VOICE:"]
        if profile.voice_description:
            parts.append(profile.voice_description)
        if profile.vocabulary:
            parts.append(f"Preferred terms: {', '.join(profile.vocabulary)}")
        if profile.avoid_words:
            parts.append(f"Never use: {', '.join(profile.avoid_words)}")
        if profile.sample_content:
            parts.append(f"Example of desired style:\n{profile.sample_content}")
        return "\n".join(parts)

    def _build_listing_section(self, listing: Listing) -> str:
        parts = ["LISTING DATA:"]
        if listing.address_full:
            parts.append(f"Address: {listing.address_full}")
        if listing.price:
            parts.append(f"Price: ${listing.price:,.0f}")
        if listing.bedrooms or listing.bathrooms:
            parts.append(f"Beds/Baths: {listing.bedrooms or '?'}BR / {listing.bathrooms or '?'}BA")
        if listing.sqft:
            parts.append(f"Sqft: {listing.sqft:,}")
        if listing.property_type:
            parts.append(f"Property Type: {listing.property_type}")
        if listing.year_built:
            parts.append(f"Year Built: {listing.year_built}")
        if listing.features:
            features_str = (
                ', '.join(listing.features)
                if isinstance(listing.features, list)
                else listing.features
            )
            parts.append(f"Key Features: {features_str}")
        if listing.description_original:
            parts.append(f"Original Description: {listing.description_original}")
        if listing.listing_agent_name:
            parts.append(f"Listing Agent: {listing.listing_agent_name}")
        if getattr(listing, "listing_agent_email", None):
            parts.append(f"Agent Email: {listing.listing_agent_email}")
        if getattr(listing, "listing_agent_phone", None):
            parts.append(f"Agent Phone: {listing.listing_agent_phone}")
        return "\n".join(parts)
