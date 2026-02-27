"""End-to-end pipeline integration test.

Exercises the full content marketing pipeline:
  1. Create a manual listing via API
  2. Generate content (AI service mocked)
  3. Send an email campaign (SendGrid mocked)
  4. Post to social media (Meta Graph API mocked)
  5. Verify all DB rows: listing, content, content_version, usage_event,
     email_campaign, social_posts
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.content_version import ContentVersion
from app.models.email_campaign import EmailCampaign
from app.models.social_post import SocialPost
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent
from app.models.user import User
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_ai_generate_result():
    """Realistic return value from AIService.generate()."""
    return {
        "body": (
            "Stunning oceanfront condo at 500 Ocean Blvd featuring 3 bedrooms, "
            "2 bathrooms, and 1800 square feet of refined coastal living. "
            "Floor-to-ceiling windows frame panoramic Atlantic views from every "
            "room. Resort-style amenities include a heated pool, fitness center, "
            "and private beach access."
        ),
        "metadata": {"word_count": 42, "character_count": 310},
        "model": "claude-sonnet-4-5-20250929",
        "prompt_tokens": 480,
        "completion_tokens": 120,
    }


def _social_settings():
    """Tenant settings with social credentials and SendGrid configured."""
    return {
        "social": {
            "page_access_token": "test-token-abc123",
            "facebook_page_id": "123456789",
            "instagram_user_id": "987654321",
        },
    }


def _mock_httpx_client():
    """Build a fully-wired async httpx mock for social service calls.

    Call sequence the social service makes:
      HEAD   (photo URL validation)
      POST   (Facebook page post)
      POST   (Instagram container creation)
      POST   (Instagram media publish)
    """
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    # HEAD for photo validation
    head_resp = AsyncMock()
    head_resp.status_code = 200
    head_resp.headers = {"content-type": "image/jpeg"}
    mock_client.head.return_value = head_resp

    # POST responses: Facebook, IG container, IG publish
    fb_resp = AsyncMock()
    fb_resp.json.return_value = {"id": "fb_post_e2e_001"}
    fb_resp.status_code = 200

    ig_container_resp = AsyncMock()
    ig_container_resp.json.return_value = {"id": "ig_container_e2e_001"}
    ig_container_resp.status_code = 200

    ig_publish_resp = AsyncMock()
    ig_publish_resp.json.return_value = {"id": "ig_post_e2e_001"}
    ig_publish_resp.status_code = 200

    mock_client.post.side_effect = [fb_resp, ig_container_resp, ig_publish_resp]

    return mock_client


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EPipeline:
    """Full content pipeline: listing -> generate -> email -> social -> DB."""

    # -- Step 1: Create listing via the manual-listing endpoint ------------

    async def test_full_pipeline(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")

        # Configure tenant with social credentials before any API calls
        test_tenant.settings = _social_settings()
        db_session.add(test_tenant)
        await db_session.flush()

        # ── 1. Create listing via POST /api/v1/listings/manual ────────

        listing_payload = {
            "address_full": "500 Ocean Blvd, Fort Lauderdale, FL 33308",
            "address_street": "500 Ocean Blvd",
            "address_city": "Fort Lauderdale",
            "address_state": "FL",
            "address_zip": "33308",
            "price": 1250000,
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 1800,
            "year_built": 2018,
            "property_type": "condo",
            "status": "active",
            "description_original": "Beautiful oceanfront condo with panoramic views.",
            "features": ["Pool", "Ocean View", "Fitness Center"],
            "photos": [{"url": "https://example.com/photo1.jpg"}],
        }

        listing_resp = await client.post(
            "/api/v1/listings/manual",
            headers=headers,
            json=listing_payload,
        )
        assert listing_resp.status_code == 201, listing_resp.text
        listing_data = listing_resp.json()
        listing_id = listing_data["id"]
        assert listing_data["address_full"] == "500 Ocean Blvd, Fort Lauderdale, FL 33308"
        assert listing_data["property_type"] == "condo"
        assert float(listing_data["price"]) == 1250000

        # ── 2. Generate content (mock AIService) ─────────────────────

        ai_result = _mock_ai_generate_result()

        with patch("app.api.v1.content.AIService") as mock_ai_cls:
            mock_ai_instance = AsyncMock()
            mock_ai_instance.generate = AsyncMock(return_value=ai_result)
            mock_ai_cls.return_value = mock_ai_instance

            gen_resp = await client.post(
                "/api/v1/content/generate",
                headers=headers,
                json={
                    "listing_id": listing_id,
                    "content_type": "listing_description",
                    "tone": "professional",
                    "variants": 1,
                },
            )

        assert gen_resp.status_code == 201, gen_resp.text
        gen_data = gen_resp.json()
        assert len(gen_data["content"]) == 1

        content_item = gen_data["content"][0]
        content_id = content_item["id"]
        assert content_item["content_type"] == "listing_description"
        assert content_item["tone"] == "professional"
        assert content_item["ai_model"] == "claude-sonnet-4-5-20250929"
        assert content_item["prompt_tokens"] == 480
        assert content_item["completion_tokens"] == 120
        assert "oceanfront" in content_item["body"].lower()

        # Verify credit consumption reported in response
        usage = gen_data["usage"]
        assert usage["credits_consumed"] == 1
        assert usage["credits_remaining"] == 999  # 1000 - 1

        # ── 3. Send email campaign (mock EmailService) ────────────────

        mock_campaign = EmailCampaign(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            content_id=uuid.UUID(content_id),
            listing_id=uuid.UUID(listing_id),
            user_id=test_user.id,
            subject="Just Listed: 500 Ocean Blvd",
            from_email="noreply@listingai.com",
            from_name="ListingAI",
            recipient_count=2,
            sent=2,
            failed=0,
            errors=[],
            campaign_type="just_listed",
        )

        with patch("app.api.v1.email_campaigns.EmailService") as mock_email_cls:
            mock_email_svc = AsyncMock()
            mock_email_svc.is_configured = True
            mock_email_svc.send_and_track = AsyncMock(return_value=mock_campaign)
            mock_email_cls.return_value = mock_email_svc

            email_resp = await client.post(
                "/api/v1/email-campaigns/send",
                headers=headers,
                json={
                    "to_emails": ["alice@example.com", "bob@example.com"],
                    "subject": "Just Listed: 500 Ocean Blvd",
                    "html_content": f"<h1>New Listing</h1><p>{content_item['body']}</p>",
                    "campaign_type": "just_listed",
                    "content_id": content_id,
                    "listing_id": listing_id,
                },
            )

        assert email_resp.status_code == 201, email_resp.text
        email_data = email_resp.json()
        assert email_data["sent"] == 2
        assert email_data["failed"] == 0
        assert email_data["campaign_id"] is not None

        # Verify send_and_track was called with correct IDs
        call_kwargs = mock_email_svc.send_and_track.call_args.kwargs
        assert call_kwargs["tenant_id"] == test_tenant.id
        assert call_kwargs["content_id"] == uuid.UUID(content_id)
        assert call_kwargs["listing_id"] == uuid.UUID(listing_id)
        assert call_kwargs["campaign_type"] == "just_listed"
        assert len(call_kwargs["to_emails"]) == 2

        # ── 4. Post to social media (mock httpx) ─────────────────────

        mock_httpx = _mock_httpx_client()

        with patch("app.services.social_service.httpx.AsyncClient", return_value=mock_httpx):
            social_resp = await client.post(
                "/api/v1/social/post",
                headers=headers,
                json={
                    "fb_text": f"Just listed! {content_item['body']}",
                    "ig_text": "Stunning oceanfront condo #realestate #fortlauderdale #oceanview",
                    "photo_url": "https://example.com/photo1.jpg",
                    "listing_link": "https://listingai.com/l/500-ocean-blvd",
                    "content_id": content_id,
                    "listing_id": listing_id,
                },
            )

        assert social_resp.status_code == 201, social_resp.text
        social_data = social_resp.json()
        platforms = {r["platform"]: r for r in social_data["results"]}
        assert platforms["facebook"]["success"] is True
        assert platforms["facebook"]["post_id"] == "fb_post_e2e_001"
        assert platforms["instagram"]["success"] is True
        assert platforms["instagram"]["post_id"] == "ig_post_e2e_001"

        # ── 5. Verify DB state ────────────────────────────────────────

        # 5a. Content row
        content_rows = (
            await db_session.execute(
                select(Content).where(
                    Content.tenant_id == test_tenant.id,
                    Content.listing_id == uuid.UUID(listing_id),
                )
            )
        ).scalars().all()
        assert len(content_rows) == 1
        c = content_rows[0]
        assert c.content_type == "listing_description"
        assert c.tone == "professional"
        assert c.ai_model == "claude-sonnet-4-5-20250929"
        assert c.prompt_tokens == 480
        assert c.completion_tokens == 120
        assert str(c.id) == content_id

        # 5b. ContentVersion row (initial version saved by ContentService.create)
        version_rows = (
            await db_session.execute(
                select(ContentVersion).where(ContentVersion.content_id == c.id)
            )
        ).scalars().all()
        assert len(version_rows) == 1
        assert version_rows[0].version == 1
        assert "oceanfront" in version_rows[0].body.lower()

        # 5c. UsageEvent row
        usage_rows = (
            await db_session.execute(
                select(UsageEvent).where(
                    UsageEvent.tenant_id == test_tenant.id,
                    UsageEvent.event_type == "content_generation",
                )
            )
        ).scalars().all()
        assert len(usage_rows) == 1
        ue = usage_rows[0]
        assert ue.credits_consumed == 1
        assert ue.content_type == "listing_description"
        assert ue.tokens_used == 480 + 120  # prompt + completion
        assert ue.user_id == test_user.id

        # 5d. SocialPost rows (one per platform)
        social_rows = (
            await db_session.execute(
                select(SocialPost).where(
                    SocialPost.tenant_id == test_tenant.id,
                    SocialPost.listing_id == uuid.UUID(listing_id),
                )
            )
        ).scalars().all()
        assert len(social_rows) == 2
        sp_by_platform = {sp.platform: sp for sp in social_rows}

        fb = sp_by_platform["facebook"]
        assert fb.status == "success"
        assert fb.platform_post_id == "fb_post_e2e_001"
        assert "Just listed!" in fb.body
        assert fb.content_id == uuid.UUID(content_id)

        ig = sp_by_platform["instagram"]
        assert ig.status == "success"
        assert ig.platform_post_id == "ig_post_e2e_001"
        assert "#realestate" in ig.body

    # -- Variant: pipeline with multiple content variants ------------------

    async def test_pipeline_multiple_variants(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ):
        """Generate 2 variants and verify both are persisted with usage tracked."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")

        # Create a listing directly in DB (faster for this sub-test)
        from decimal import Decimal

        from app.models.listing import Listing

        listing = Listing(
            tenant_id=test_tenant.id,
            address_full="200 Sunrise Ave, Palm Beach, FL 33480",
            address_street="200 Sunrise Ave",
            address_city="Palm Beach",
            address_state="FL",
            address_zip="33480",
            price=Decimal("2500000"),
            bedrooms=4,
            bathrooms=Decimal("3.5"),
            sqft=3200,
            year_built=2020,
            property_type="condo",
            status="active",
        )
        db_session.add(listing)
        await db_session.flush()

        variant_a = _mock_ai_generate_result()
        variant_b = {
            **_mock_ai_generate_result(),
            "body": (
                "Experience unparalleled luxury at 200 Sunrise Ave. This "
                "exquisite 4-bedroom residence offers breathtaking views and "
                "world-class amenities in the heart of Palm Beach."
            ),
        }

        with patch("app.api.v1.content.AIService") as mock_ai_cls:
            mock_ai_instance = AsyncMock()
            mock_ai_instance.generate = AsyncMock(
                side_effect=[variant_a, variant_b]
            )
            mock_ai_cls.return_value = mock_ai_instance

            gen_resp = await client.post(
                "/api/v1/content/generate",
                headers=headers,
                json={
                    "listing_id": str(listing.id),
                    "content_type": "social_facebook",
                    "tone": "luxury",
                    "variants": 2,
                },
            )

        assert gen_resp.status_code == 201, gen_resp.text
        gen_data = gen_resp.json()
        assert len(gen_data["content"]) == 2
        assert gen_data["usage"]["credits_consumed"] == 2
        assert gen_data["usage"]["credits_remaining"] == 998  # 1000 - 2

        # Verify both content rows exist
        content_rows = (
            await db_session.execute(
                select(Content).where(
                    Content.tenant_id == test_tenant.id,
                    Content.listing_id == listing.id,
                )
            )
        ).scalars().all()
        assert len(content_rows) == 2

        # Verify 2 usage events
        usage_rows = (
            await db_session.execute(
                select(UsageEvent).where(
                    UsageEvent.tenant_id == test_tenant.id,
                    UsageEvent.event_type == "content_generation",
                )
            )
        ).scalars().all()
        assert len(usage_rows) == 2
        assert all(u.credits_consumed == 1 for u in usage_rows)

    # -- Variant: credit exhaustion mid-pipeline ---------------------------

    async def test_pipeline_credit_exhaustion(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ):
        """When credits run out, generation returns 402."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")

        # Set limit to 0 so no credits remain
        test_tenant.monthly_generation_limit = 0
        db_session.add(test_tenant)
        await db_session.flush()

        # Create listing via API
        listing_resp = await client.post(
            "/api/v1/listings/manual",
            headers=headers,
            json={
                "address_full": "999 Broke St, Miami, FL 33101",
                "price": 100000,
                "property_type": "residential",
            },
        )
        assert listing_resp.status_code == 201
        listing_id = listing_resp.json()["id"]

        gen_resp = await client.post(
            "/api/v1/content/generate",
            headers=headers,
            json={
                "listing_id": listing_id,
                "content_type": "listing_description",
                "tone": "professional",
                "variants": 1,
            },
        )
        assert gen_resp.status_code == 402
        assert "Insufficient credits" in gen_resp.json()["detail"]

    # -- Variant: social fails without credentials -------------------------

    async def test_pipeline_social_no_credentials(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ):
        """Social posting without credentials returns 400."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")

        # Ensure tenant has no social settings
        test_tenant.settings = {}
        db_session.add(test_tenant)
        await db_session.flush()

        social_resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={"fb_text": "This should fail"},
        )
        assert social_resp.status_code == 400
        assert "credentials" in social_resp.json()["detail"].lower()

    # -- Variant: email service not configured -----------------------------

    async def test_pipeline_email_not_configured(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ):
        """Email send without SendGrid key returns 400."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")

        with patch("app.api.v1.email_campaigns.EmailService") as mock_email_cls:
            mock_email_cls.return_value.is_configured = False

            email_resp = await client.post(
                "/api/v1/email-campaigns/send",
                headers=headers,
                json={
                    "to_emails": ["a@example.com"],
                    "subject": "Test",
                    "html_content": "<p>body</p>",
                },
            )
        assert email_resp.status_code == 400
        assert "sendgrid" in email_resp.json()["detail"].lower()
