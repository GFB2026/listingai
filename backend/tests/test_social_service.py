"""Tests for SocialService (Meta Graph API) and photo URL validation."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.social_service import SocialService, validate_photo_url


class TestValidatePhotoUrl:
    @pytest.mark.asyncio
    async def test_empty_url(self):
        result = await validate_photo_url("")
        assert result["valid"] is False
        assert "empty" in result["error"]

    @pytest.mark.asyncio
    async def test_bad_scheme(self):
        result = await validate_photo_url("ftp://example.com/photo.jpg")
        assert result["valid"] is False
        assert "http://" in result["error"]

    @pytest.mark.asyncio
    async def test_valid_image_url(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg"}

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=mock_response):
            result = await validate_photo_url("https://example.com/photo.jpg")

        assert result["valid"] is True
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_non_image_content_type(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=mock_response):
            result = await validate_photo_url("https://example.com/page")

        assert result["valid"] is False
        assert "text/html" in result["error"]

    @pytest.mark.asyncio
    async def test_404_url(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=mock_response):
            result = await validate_photo_url("https://example.com/missing.jpg")

        assert result["valid"] is False
        assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_timeout(self):
        with patch("httpx.AsyncClient.head", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            result = await validate_photo_url("https://example.com/slow.jpg")

        assert result["valid"] is False
        assert "timed out" in result["error"]


class TestSocialServiceInit:
    def test_from_tenant_settings_configured(self):
        settings = {
            "social": {
                "page_access_token": "token123",
                "facebook_page_id": "page456",
                "instagram_user_id": "ig789",
            }
        }
        service = SocialService.from_tenant_settings(settings)
        assert service is not None
        assert service.token == "token123"
        assert service.page_id == "page456"
        assert service.ig_user_id == "ig789"
        assert service.has_instagram is True

    def test_from_tenant_settings_missing_token(self):
        settings = {"social": {"facebook_page_id": "page456"}}
        service = SocialService.from_tenant_settings(settings)
        assert service is None

    def test_from_tenant_settings_empty(self):
        service = SocialService.from_tenant_settings({})
        assert service is None

    def test_from_tenant_settings_no_instagram(self):
        settings = {
            "social": {
                "page_access_token": "token",
                "facebook_page_id": "page",
            }
        }
        service = SocialService.from_tenant_settings(settings)
        assert service is not None
        assert service.has_instagram is False


class TestPostToFacebook:
    @pytest.mark.asyncio
    async def test_successful_text_post(self):
        service = SocialService("token", "page123")

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "post_789"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await service.post_to_facebook("Hello world!")

        assert result["success"] is True
        assert result["post_id"] == "post_789"

    @pytest.mark.asyncio
    async def test_api_error(self):
        service = SocialService("token", "page123")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {"message": "Invalid token"}
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await service.post_to_facebook("Hello")

        assert result["success"] is False
        assert "Invalid token" in result["error"]

    @pytest.mark.asyncio
    async def test_timeout(self):
        service = SocialService("token", "page123")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            result = await service.post_to_facebook("Hello")

        assert result["success"] is False
        assert "timed out" in result["error"]


class TestPostToInstagram:
    @pytest.mark.asyncio
    async def test_no_ig_user_id(self):
        service = SocialService("token", "page123", ig_user_id=None)
        result = await service.post_to_instagram("Caption", "https://img.com/photo.jpg")
        assert result["success"] is False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_two_step_flow(self):
        service = SocialService("token", "page123", ig_user_id="ig456")

        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            if call_count == 1:
                resp.json.return_value = {"id": "container_001"}
            else:
                resp.json.return_value = {"id": "ig_post_002"}
            return resp

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
            result = await service.post_to_instagram("Nice photo!", "https://img.com/photo.jpg")

        assert result["success"] is True
        assert result["post_id"] == "ig_post_002"
        assert call_count == 2


class TestPostListing:
    @pytest.mark.asyncio
    async def test_skips_photo_on_validation_failure(self):
        service = SocialService("token", "page123")

        # Mock validate_photo_url to fail
        mock_validate = AsyncMock(return_value={"valid": False, "error": "HTTP 404"})
        mock_fb_response = MagicMock()
        mock_fb_response.json.return_value = {"id": "post_ok"}

        with (
            patch("app.services.social_service.validate_photo_url", mock_validate),
            patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_fb_response),
        ):
            results = await service.post_listing(
                fb_text="Check this out!",
                photo_url="https://bad-url.com/gone.jpg",
            )

        # Facebook should still succeed (text-only fallback)
        assert results["facebook"]["success"] is True

    @pytest.mark.asyncio
    async def test_instagram_fails_with_bad_photo(self):
        service = SocialService("token", "page123", ig_user_id="ig456")

        mock_validate = AsyncMock(return_value={"valid": False, "error": "not reachable"})

        with patch("app.services.social_service.validate_photo_url", mock_validate):
            results = await service.post_listing(
                ig_text="Beautiful view!",
                photo_url="https://bad-url.com/gone.jpg",
            )

        assert results["instagram"]["success"] is False
        assert "validation failed" in results["instagram"]["error"].lower()
