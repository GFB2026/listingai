"""Tests for EmailService (SendGrid integration)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.email_service import EmailService, _canspam_footer, parse_subject_from_email


class TestParseSubjectFromEmail:
    def test_extracts_subject_line(self):
        text = "Subject: Open House This Weekend!\n\nBody text here."
        assert parse_subject_from_email(text) == "Open House This Weekend!"

    def test_fallback_when_no_subject(self):
        text = "Just some body text without a subject."
        assert parse_subject_from_email(text) == "New Listing Available"

    def test_case_insensitive(self):
        text = "SUBJECT: Great Deal\nPreheader: Check it out"
        assert parse_subject_from_email(text) == "Great Deal"


class TestCanspamFooter:
    def test_includes_physical_address(self):
        footer = _canspam_footer("123 Main St, City, ST 12345")
        assert "123 Main St" in footer
        assert "Unsubscribe" in footer

    def test_includes_unsubscribe_url(self):
        footer = _canspam_footer(
            "123 Main St",
            unsubscribe_url="https://example.com/unsub",
        )
        assert "https://example.com/unsub" in footer

    def test_includes_brokerage_name(self):
        footer = _canspam_footer("123 Main St", brokerage_name="Test Realty")
        assert "Test Realty" in footer

    def test_mailto_fallback_when_no_url(self):
        footer = _canspam_footer("123 Main St")
        assert "mailto:" in footer


class TestEmailServiceInit:
    def test_defaults_from_settings(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = "sg-test-key"
            mock.return_value.sendgrid_default_from_email = "from@test.com"
            mock.return_value.sendgrid_default_from_name = "TestApp"
            service = EmailService()

        assert service.api_key == "sg-test-key"
        assert service.from_email == "from@test.com"
        assert service.from_name == "TestApp"

    def test_overrides(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = "default"
            mock.return_value.sendgrid_default_from_email = "default@test.com"
            mock.return_value.sendgrid_default_from_name = "Default"
            service = EmailService(
                api_key="custom-key",
                from_email="custom@test.com",
                from_name="Custom",
            )

        assert service.api_key == "custom-key"
        assert service.from_email == "custom@test.com"

    def test_is_configured(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = ""
            mock.return_value.sendgrid_default_from_email = ""
            mock.return_value.sendgrid_default_from_name = ""
            service = EmailService()
        assert service.is_configured is False


class TestEmailServiceSend:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_error(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = ""
            mock.return_value.sendgrid_default_from_email = ""
            mock.return_value.sendgrid_default_from_name = ""
            service = EmailService()

        result = await service.send(["test@test.com"], "Subject", "<p>Body</p>")
        assert result["sent"] == 0
        assert "not configured" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_no_recipients_returns_error(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = "key"
            mock.return_value.sendgrid_default_from_email = "a@b.com"
            mock.return_value.sendgrid_default_from_name = "Test"
            service = EmailService()

        result = await service.send([], "Subject", "<p>Body</p>")
        assert result["sent"] == 0
        assert "No recipients" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_successful_send(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = "sg-key"
            mock.return_value.sendgrid_default_from_email = "from@test.com"
            mock.return_value.sendgrid_default_from_name = "Test"
            service = EmailService()

        mock_response = MagicMock()
        mock_response.status_code = 202

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await service.send(
                ["user1@test.com", "user2@test.com"],
                "Test Subject",
                "<p>Hello</p>",
            )

        assert result["sent"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = "sg-key"
            mock.return_value.sendgrid_default_from_email = "from@test.com"
            mock.return_value.sendgrid_default_from_name = "Test"
            service = EmailService()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            result = await service.send(["user@test.com"], "Subject", "<p>Body</p>")

        assert result["failed"] == 1
        assert "timed out" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_canspam_footer_appended(self):
        with patch("app.services.email_service.get_settings") as mock:
            mock.return_value.sendgrid_api_key = "sg-key"
            mock.return_value.sendgrid_default_from_email = "from@test.com"
            mock.return_value.sendgrid_default_from_name = "Test"
            service = EmailService()

        mock_response = MagicMock()
        mock_response.status_code = 202
        captured_payload = {}

        async def capture_post(url, json=None, **kwargs):
            captured_payload.update(json)
            return mock_response

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=capture_post):
            await service.send(
                ["user@test.com"],
                "Subject",
                "<html><body><p>Hello</p></body></html>",
                physical_address="123 Main St, City, ST 12345",
            )

        html = captured_payload["content"][0]["value"]
        assert "123 Main St" in html
        assert "Unsubscribe" in html
