"""Tests for PromptBuilder — especially event content types and placeholder substitution."""

from unittest.mock import MagicMock


from app.services.prompt_builder import PromptBuilder, SYSTEM_PROMPTS


def _mock_listing(**overrides):
    """Create a mock Listing with sensible defaults."""
    defaults = {
        "address_full": "100 Ocean Blvd, Fort Lauderdale, FL 33308",
        "price": 1500000,
        "bedrooms": 3,
        "bathrooms": 2.5,
        "sqft": 2200,
        "property_type": "condo",
        "year_built": 2015,
        "features": ["Pool", "Ocean View", "Balcony"],
        "description_original": "Beautiful oceanfront condo.",
        "listing_agent_name": "Dennis Matson",
        "listing_agent_email": "dennis@galtoceanrealty.com",
        "listing_agent_phone": "(954) 817-8555",
    }
    defaults.update(overrides)
    listing = MagicMock()
    for k, v in defaults.items():
        setattr(listing, k, v)
    return listing


def _mock_brand(**overrides):
    """Create a mock BrandProfile."""
    defaults = {
        "voice_description": "Professional and warm",
        "vocabulary": ["coastal", "premier"],
        "avoid_words": ["cheap", "fixer-upper"],
        "sample_content": None,
    }
    defaults.update(overrides)
    profile = MagicMock()
    for k, v in defaults.items():
        setattr(profile, k, v)
    return profile


class TestPromptBuilderBasics:
    def test_all_content_types_have_system_prompts(self):
        expected = {
            "listing_description", "social_instagram", "social_facebook",
            "social_linkedin", "social_x", "email_just_listed",
            "email_open_house", "email_drip", "flyer", "video_script",
            "open_house_invite", "price_reduction", "just_sold",
        }
        assert set(SYSTEM_PROMPTS.keys()) == expected

    def test_build_returns_system_and_user(self):
        builder = PromptBuilder()
        system, user = builder.build(
            listing=_mock_listing(),
            content_type="listing_description",
            tone="professional",
        )
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert "LISTING DATA:" in user
        assert "100 Ocean Blvd" in user

    def test_tone_substitution(self):
        builder = PromptBuilder()
        system, _ = builder.build(
            listing=_mock_listing(),
            content_type="listing_description",
            tone="luxury",
        )
        assert "luxury" in system
        assert "{tone}" not in system

    def test_brand_profile_injected(self):
        builder = PromptBuilder()
        system, _ = builder.build(
            listing=_mock_listing(),
            content_type="listing_description",
            tone="professional",
            brand_profile=_mock_brand(),
        )
        assert "BRAND VOICE:" in system
        assert "Professional and warm" in system
        assert "coastal" in system
        assert "cheap" in system

    def test_instructions_appended(self):
        builder = PromptBuilder()
        _, user = builder.build(
            listing=_mock_listing(),
            content_type="listing_description",
            tone="professional",
            instructions="Focus on the ocean view.",
        )
        assert "ADDITIONAL INSTRUCTIONS:" in user
        assert "Focus on the ocean view." in user

    def test_unknown_content_type_falls_back(self):
        builder = PromptBuilder()
        system, _ = builder.build(
            listing=_mock_listing(),
            content_type="nonexistent_type",
            tone="professional",
        )
        # Should fall back to listing description system prompt
        assert isinstance(system, str)
        assert len(system) > 50


class TestEventContentTypes:
    def test_open_house_invite_substitutes_event_details(self):
        builder = PromptBuilder()
        event_details = "Sunday March 1, 1-4 PM"
        system, _ = builder.build(
            listing=_mock_listing(),
            content_type="open_house_invite",
            tone="professional",
            event_details=event_details,
        )
        assert event_details in system
        assert "{event_details}" not in system
        assert "open house" in system.lower()

    def test_price_reduction_substitutes_event_details(self):
        builder = PromptBuilder()
        event_details = (
            "Price reduced from $1,800,000 to $1,500,000"
            " ($300,000 off, 16.7% reduction)."
        )
        system, _ = builder.build(
            listing=_mock_listing(),
            content_type="price_reduction",
            tone="professional",
            event_details=event_details,
        )
        assert event_details in system
        assert "{event_details}" not in system
        assert "price reduction" in system.lower()

    def test_just_sold_substitutes_event_details(self):
        builder = PromptBuilder()
        event_details = "Previously listed at $1,500,000. Sold for $1,450,000."
        system, _ = builder.build(
            listing=_mock_listing(),
            content_type="just_sold",
            tone="professional",
            event_details=event_details,
        )
        assert event_details in system
        assert "{event_details}" not in system
        assert "just sold" in system.lower()

    def test_event_details_empty_when_not_provided(self):
        builder = PromptBuilder()
        system, _ = builder.build(
            listing=_mock_listing(),
            content_type="open_house_invite",
            tone="professional",
        )
        # event_details defaults to "" — placeholder should be gone
        assert "{event_details}" not in system

    def test_event_prompts_include_tone(self):
        builder = PromptBuilder()
        for ct in ("open_house_invite", "price_reduction", "just_sold"):
            system, _ = builder.build(
                listing=_mock_listing(),
                content_type=ct,
                tone="luxury",
                event_details="test details",
            )
            assert "luxury" in system, f"{ct} should include tone"
            assert "{tone}" not in system, f"{ct} should not have raw {{tone}} placeholder"


class TestListingDataSection:
    def test_includes_all_listing_fields(self):
        builder = PromptBuilder()
        _, user = builder.build(
            listing=_mock_listing(),
            content_type="listing_description",
            tone="professional",
        )
        assert "$1,500,000" in user
        assert "3BR" in user
        assert "2.5BA" in user or "2.5" in user
        assert "2,200" in user
        assert "Pool" in user
        assert "Dennis Matson" in user

    def test_agent_contact_in_prompt(self):
        builder = PromptBuilder()
        _, user = builder.build(
            listing=_mock_listing(),
            content_type="email_just_listed",
            tone="professional",
        )
        assert "dennis@galtoceanrealty.com" in user
        assert "(954) 817-8555" in user

    def test_minimal_listing(self):
        """Listing with minimal data should not crash."""
        builder = PromptBuilder()
        listing = _mock_listing(
            price=None, bedrooms=None, bathrooms=None,
            sqft=None, year_built=None, features=None,
            description_original=None, listing_agent_name=None,
            listing_agent_email=None, listing_agent_phone=None,
        )
        _, user = builder.build(
            listing=listing,
            content_type="listing_description",
            tone="professional",
        )
        assert "LISTING DATA:" in user
        assert "100 Ocean Blvd" in user
