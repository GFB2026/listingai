"""Tests for email campaign API endpoints: send, list, status."""

import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_campaign import EmailCampaign
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


# ── Auth ──────────────────────────────────────────────────────────


class TestEmailAuth:
    async def test_send_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            json={
                "to_emails": ["a@example.com"],
                "subject": "Test",
                "html_content": "<p>Hello</p>",
            },
        )
        assert resp.status_code in (401, 403)

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/email-campaigns")
        assert resp.status_code in (401, 403)

    async def test_status_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/email-campaigns/status")
        assert resp.status_code in (401, 403)


# ── Status ────────────────────────────────────────────────────────


class TestEmailStatus:
    async def test_not_configured(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """When SENDGRID_API_KEY is not set, status returns False."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value.sendgrid_api_key = ""
            mock_settings.return_value.sendgrid_default_from_email = ""
            mock_settings.return_value.sendgrid_default_from_name = ""

            headers = await auth_headers(client, "test@example.com", "testpassword123")
            resp = await client.get("/api/v1/email-campaigns/status", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["configured"] is False

    async def test_configured(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """When SENDGRID_API_KEY is set, status returns True."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value.sendgrid_api_key = "SG.test-key"
            mock_settings.return_value.sendgrid_default_from_email = "noreply@test.com"
            mock_settings.return_value.sendgrid_default_from_name = "Test"

            headers = await auth_headers(client, "test@example.com", "testpassword123")
            resp = await client.get("/api/v1/email-campaigns/status", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["configured"] is True


# ── Validation ────────────────────────────────────────────────────


class TestEmailSendValidation:
    async def test_missing_to_emails(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={"subject": "Hi", "html_content": "<p>body</p>"},
        )
        assert resp.status_code == 422

    async def test_empty_to_emails(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={"to_emails": [], "subject": "Hi", "html_content": "<p>body</p>"},
        )
        assert resp.status_code == 422

    async def test_missing_subject(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={"to_emails": ["a@b.com"], "html_content": "<p>body</p>"},
        )
        assert resp.status_code == 422

    async def test_missing_html_content(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={"to_emails": ["a@b.com"], "subject": "Hi"},
        )
        assert resp.status_code == 422

    async def test_not_configured_returns_400(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """When SendGrid key is empty, send returns 400."""
        with patch("app.api.v1.email_campaigns.EmailService") as mock_cls:
            mock_cls.return_value.is_configured = False

            headers = await auth_headers(client, "test@example.com", "testpassword123")
            resp = await client.post(
                "/api/v1/email-campaigns/send",
                headers=headers,
                json={
                    "to_emails": ["recipient@example.com"],
                    "subject": "Test Campaign",
                    "html_content": "<p>Hello</p>",
                },
            )
            assert resp.status_code == 400
            assert "sendgrid" in resp.json()["detail"].lower()


# ── Send ──────────────────────────────────────────────────────────


class TestEmailSend:
    @patch("app.api.v1.email_campaigns.EmailService")
    async def test_send_success(
        self,
        mock_email_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        mock_service = AsyncMock()
        mock_service.is_configured = True
        mock_campaign = EmailCampaign(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            subject="Just Listed!",
            from_email="noreply@test.com",
            from_name="Test",
            recipient_count=2,
            sent=2,
            failed=0,
            errors=[],
            campaign_type="just_listed",
        )
        mock_service.send_and_track = AsyncMock(return_value=mock_campaign)
        mock_email_cls.return_value = mock_service

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={
                "to_emails": ["alice@example.com", "bob@example.com"],
                "subject": "Just Listed!",
                "html_content": "<h1>New Listing</h1><p>Check it out!</p>",
                "campaign_type": "just_listed",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["sent"] == 2
        assert data["failed"] == 0
        assert data["campaign_id"] is not None

    @patch("app.api.v1.email_campaigns.EmailService")
    async def test_send_partial_failure(
        self,
        mock_email_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        mock_service = AsyncMock()
        mock_service.is_configured = True
        mock_campaign = EmailCampaign(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            subject="Test",
            from_email="noreply@test.com",
            recipient_count=3,
            sent=2,
            failed=1,
            errors=["SendGrid request timed out"],
            campaign_type="manual",
        )
        mock_service.send_and_track = AsyncMock(return_value=mock_campaign)
        mock_email_cls.return_value = mock_service

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={
                "to_emails": ["a@b.com", "c@d.com", "e@f.com"],
                "subject": "Test",
                "html_content": "<p>body</p>",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["sent"] == 2
        assert data["failed"] == 1
        assert len(data["errors"]) == 1

    @patch("app.api.v1.email_campaigns.EmailService")
    async def test_send_with_listing_id(
        self,
        mock_email_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        test_listing,
        db_session: AsyncSession,
    ):
        mock_service = AsyncMock()
        mock_service.is_configured = True
        mock_campaign = EmailCampaign(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            listing_id=test_listing.id,
            subject="New listing",
            from_email="noreply@test.com",
            recipient_count=1,
            sent=1,
            failed=0,
            errors=[],
            campaign_type="just_listed",
        )
        mock_service.send_and_track = AsyncMock(return_value=mock_campaign)
        mock_email_cls.return_value = mock_service

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={
                "to_emails": ["x@y.com"],
                "subject": "New listing",
                "html_content": "<p>body</p>",
                "listing_id": str(test_listing.id),
                "campaign_type": "just_listed",
            },
        )
        assert resp.status_code == 201

        # Verify send_and_track was called with listing_id
        call_kwargs = mock_service.send_and_track.call_args.kwargs
        assert call_kwargs["listing_id"] == test_listing.id

    @patch("app.api.v1.email_campaigns.EmailService")
    async def test_send_default_campaign_type(
        self,
        mock_email_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        mock_service = AsyncMock()
        mock_service.is_configured = True
        mock_campaign = EmailCampaign(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            subject="Test",
            from_email="noreply@test.com",
            recipient_count=1,
            sent=1,
            failed=0,
            errors=[],
            campaign_type="manual",
        )
        mock_service.send_and_track = AsyncMock(return_value=mock_campaign)
        mock_email_cls.return_value = mock_service

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/email-campaigns/send",
            headers=headers,
            json={
                "to_emails": ["a@b.com"],
                "subject": "Test",
                "html_content": "<p>body</p>",
            },
        )
        assert resp.status_code == 201
        call_kwargs = mock_service.send_and_track.call_args.kwargs
        assert call_kwargs["campaign_type"] == "manual"


# ── List Campaigns ────────────────────────────────────────────────


class TestListCampaigns:
    async def test_empty_list(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/email-campaigns", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["campaigns"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_list_with_campaigns(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        # Insert campaigns directly
        for i in range(3):
            campaign = EmailCampaign(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                subject=f"Campaign {i+1}",
                from_email="noreply@test.com",
                from_name="Test",
                recipient_count=10,
                sent=10,
                failed=0,
                errors=[],
                campaign_type="just_listed",
            )
            db_session.add(campaign)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/email-campaigns", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["campaigns"]) == 3

    async def test_filter_by_campaign_type(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        for ct in ["just_listed", "just_listed", "open_house"]:
            db_session.add(EmailCampaign(
                tenant_id=test_tenant.id,
                subject=f"Test {ct}",
                from_email="noreply@test.com",
                recipient_count=5,
                sent=5,
                failed=0,
                campaign_type=ct,
            ))
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            "/api/v1/email-campaigns?campaign_type=just_listed", headers=headers
        )
        data = resp.json()
        assert data["total"] == 2
        assert all(c["campaign_type"] == "just_listed" for c in data["campaigns"])

    async def test_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        for i in range(5):
            db_session.add(EmailCampaign(
                tenant_id=test_tenant.id,
                subject=f"Campaign {i}",
                from_email="noreply@test.com",
                recipient_count=1,
                sent=1,
                failed=0,
                campaign_type="manual",
            ))
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")

        resp = await client.get(
            "/api/v1/email-campaigns?page=1&page_size=2", headers=headers
        )
        data = resp.json()
        assert data["total"] == 5
        assert len(data["campaigns"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

        resp2 = await client.get(
            "/api/v1/email-campaigns?page=3&page_size=2", headers=headers
        )
        data2 = resp2.json()
        assert len(data2["campaigns"]) == 1  # 5 items, page 3 of size 2 = 1

    async def test_response_shape(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        db_session.add(EmailCampaign(
            tenant_id=test_tenant.id,
            subject="Shape Test",
            from_email="noreply@test.com",
            from_name="Tester",
            recipient_count=42,
            sent=40,
            failed=2,
            errors=["Some error"],
            campaign_type="price_reduction",
        ))
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/email-campaigns", headers=headers)
        data = resp.json()
        c = data["campaigns"][0]
        assert c["subject"] == "Shape Test"
        assert c["from_email"] == "noreply@test.com"
        assert c["from_name"] == "Tester"
        assert c["recipient_count"] == 42
        assert c["sent"] == 40
        assert c["failed"] == 2
        assert c["campaign_type"] == "price_reduction"
        assert "id" in c
        assert "created_at" in c


# ── Tenant Isolation ──────────────────────────────────────────────


class TestEmailIsolation:
    async def test_other_tenant_cannot_see_campaigns(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        other_user: User,
        other_tenant: Tenant,
        db_session: AsyncSession,
    ):
        # Add campaign to test_tenant
        db_session.add(EmailCampaign(
            tenant_id=test_tenant.id,
            subject="Secret Campaign",
            from_email="noreply@test.com",
            recipient_count=1,
            sent=1,
            failed=0,
            campaign_type="manual",
        ))
        await db_session.flush()

        # Other tenant should not see it
        h2 = await auth_headers(client, "other@example.com", "Otherpassword1!")
        resp = await client.get("/api/v1/email-campaigns", headers=h2)
        data = resp.json()
        assert data["total"] == 0
        assert data["campaigns"] == []

        # Test tenant should see it
        h1 = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/email-campaigns", headers=h1)
        data = resp.json()
        assert data["total"] == 1
