from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def test_build_listing_section(self):
        builder = PromptBuilder()

        listing = MagicMock()
        listing.address_full = "4250 Galt Ocean Dr, Fort Lauderdale, FL 33308"
        listing.price = 1500000
        listing.bedrooms = 3
        listing.bathrooms = 2.5
        listing.sqft = 2200
        listing.property_type = "condo"
        listing.year_built = 2020
        listing.features = ["Ocean View", "Pool", "Renovated Kitchen"]
        listing.description_original = "Beautiful ocean view condo"
        listing.listing_agent_name = "Dennis Test"

        result = builder._build_listing_section(listing)

        assert "4250 Galt Ocean Dr" in result
        assert "$1,500,000" in result
        assert "3BR" in result
        assert "2.5BA" in result
        assert "2,200" in result
        assert "Ocean View" in result

    def test_build_brand_section(self):
        builder = PromptBuilder()

        profile = MagicMock()
        profile.voice_description = "Luxury and sophisticated"
        profile.vocabulary = ["coastal", "exclusive", "premier"]
        profile.avoid_words = ["cheap", "deal"]
        profile.sample_content = "Experience the finest in coastal living."

        result = builder._build_brand_section(profile)

        assert "BRAND VOICE:" in result
        assert "Luxury and sophisticated" in result
        assert "coastal" in result
        assert "cheap" in result

    def test_build_returns_system_and_user_prompts(self):
        builder = PromptBuilder()

        listing = MagicMock()
        listing.address_full = "123 Test St"
        listing.price = 500000
        listing.bedrooms = 2
        listing.bathrooms = 1
        listing.sqft = 1000
        listing.property_type = "residential"
        listing.year_built = 2010
        listing.features = []
        listing.description_original = None
        listing.listing_agent_name = None

        system, user = builder.build(
            listing=listing,
            content_type="social_instagram",
            tone="luxury",
        )

        assert "Instagram" in system
        assert "luxury" in system
        assert "123 Test St" in user
        assert "Generate the content now." in user
