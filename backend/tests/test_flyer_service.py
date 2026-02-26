"""Tests for FlyerService (PPTX + PDF flyer generation)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.flyer_service import (
    BrandingConfig,
    FlyerService,
    _build_qr_url,
    _build_specs,
    _extract_body_copy,
    _sanitize_text,
)


class TestBrandingConfig:
    def test_defaults(self):
        config = BrandingConfig()
        assert config.brokerage_name == "Your Brokerage"
        assert config.accent_color_hex == "#CC0000"
        assert config.headline == "Just Listed"

    def test_from_settings(self):
        settings = {
            "flyer": {
                "brokerage_name": "Test Realty",
                "brokerage_phone": "(555) 123-4567",
                "accent_color": "#0000FF",
                "tagline": "Your Dream Home Awaits",
            }
        }
        config = BrandingConfig.from_settings(settings)
        assert config.brokerage_name == "Test Realty"
        assert config.brokerage_phone == "(555) 123-4567"
        assert config.accent_color_hex == "#0000FF"
        assert config.tagline == "Your Dream Home Awaits"

    def test_from_settings_with_overrides(self):
        settings = {"flyer": {"brokerage_name": "From Settings"}}
        config = BrandingConfig.from_settings(settings, headline="Price Reduced")
        assert config.brokerage_name == "From Settings"
        assert config.headline == "Price Reduced"

    def test_from_empty_settings(self):
        config = BrandingConfig.from_settings({})
        assert config.brokerage_name == "Your Brokerage"


class TestHelpers:
    def test_extract_body_copy_strips_markdown(self):
        text = "# Headline\n---\nShort line.\nThis is a longer body paragraph that exceeds sixty characters in total length for selection."
        body = _extract_body_copy(text)
        assert "Headline" not in body
        assert "---" not in body
        assert "body paragraph" in body

    def test_extract_body_copy_plain_text(self):
        text = "Just a simple paragraph of marketing copy."
        body = _extract_body_copy(text)
        assert "simple paragraph" in body

    def test_build_specs(self):
        listing_data = {
            "price": 1500000,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "sqft": 2200,
        }
        specs = _build_specs(listing_data)
        assert isinstance(specs, list)
        joined = " ".join(specs)
        assert "$1,500,000" in joined
        assert "3 Bed" in joined
        assert "2.5 Bath" in joined
        assert "2,200" in joined

    def test_build_specs_missing_fields(self):
        listing_data = {"bedrooms": 2, "bathrooms": 1}
        specs = _build_specs(listing_data)
        joined = " ".join(specs)
        assert "2 Bed" in joined
        assert "$" not in joined  # no price

    def test_build_qr_url(self):
        branding = BrandingConfig(qr_base_url="https://app.example.com/listings")
        url = _build_qr_url({"mls_listing_id": "MLS123"}, branding)
        assert "https://app.example.com/listings" in url
        assert "MLS123" in url

    def test_build_qr_url_empty_base_falls_back_to_maps(self):
        branding = BrandingConfig(qr_base_url="")
        url = _build_qr_url({"address_full": "100 Ocean Blvd"}, branding)
        assert "google.com/maps" in url

    def test_sanitize_text_strips_non_latin1(self):
        text = "Hello \u2014 World \u201c quotes \u201d"
        result = _sanitize_text(text)
        # Should not raise and should produce clean output
        assert isinstance(result, str)
        assert "Hello" in result
        assert "World" in result


class TestFlyerService:
    def _sample_listing_data(self):
        return {
            "address_full": "100 Ocean Blvd, Fort Lauderdale, FL 33308",
            "price": 1500000,
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 2200,
            "lot_sqft": None,
            "year_built": 2015,
            "features": ["Pool", "Ocean View", "Balcony", "Garage"],
            "listing_agent_name": "Test Agent",
            "listing_agent_email": "agent@test.com",
            "listing_agent_phone": "(555) 000-1234",
            "property_type": "condo",
        }

    def test_generate_pptx_returns_bytesio(self):
        branding = BrandingConfig(brokerage_name="Test Realty")
        service = FlyerService(branding)

        try:
            result = service.generate_pptx(
                self._sample_listing_data(),
                "Beautiful oceanfront property with stunning views.",
            )
            assert result is not None
            result.seek(0)
            # PPTX files start with PK (ZIP format)
            header = result.read(2)
            assert header == b"PK"
        except ImportError:
            pytest.skip("python-pptx not installed")

    def test_generate_pdf_returns_bytesio(self):
        branding = BrandingConfig(brokerage_name="Test Realty")
        service = FlyerService(branding)

        try:
            result = service.generate_pdf(
                self._sample_listing_data(),
                "Beautiful oceanfront property with stunning views.",
            )
            assert result is not None
            result.seek(0)
            # PDF files start with %PDF
            header = result.read(4)
            assert header == b"%PDF"
        except ImportError:
            pytest.skip("fpdf2 not installed")
