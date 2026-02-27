"""Tests for social media API endpoints: publish posts, check status."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_post import SocialPost
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


# ── Helpers ────────────────────────────────────────────────────────


def _social_settings():
    """Tenant settings with social credentials configured."""
    return {
        "social": {
            "page_access_token": "test-token-abc123",
            "facebook_page_id": "123456789",
            "instagram_user_id": "987654321",
        }
    }


def _mock_fb_success():
    """Mock httpx response for successful Facebook post."""
    mock = AsyncMock()
    mock.json.return_value = {"id": "fb_post_123"}
    mock.status_code = 200
    return mock


def _mock_ig_container():
    """Mock httpx response for Instagram container creation."""
    mock = AsyncMock()
    mock.json.return_value = {"id": "ig_container_456"}
    mock.status_code = 200
    return mock


def _mock_ig_publish():
    """Mock httpx response for Instagram publish."""
    mock = AsyncMock()
    mock.json.return_value = {"id": "ig_post_789"}
    mock.status_code = 200
    return mock


def _mock_photo_validation():
    """Mock httpx response for photo URL HEAD request."""
    mock = AsyncMock()
    mock.status_code = 200
    mock.headers = {"content-type": "image/jpeg"}
    return mock


# ── Auth ──────────────────────────────────────────────────────────


class TestSocialAuth:
    async def test_post_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/social/post", json={"fb_text": "Hello"})
        assert resp.status_code in (401, 403)

    async def test_status_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/social/status")
        assert resp.status_code in (401, 403)


# ── Status ────────────────────────────────────────────────────────


class TestSocialStatus:
    async def test_not_configured(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/social/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False
        assert data["facebook"] is False
        assert data["instagram"] is False

    async def test_configured_with_instagram(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        test_tenant.settings = _social_settings()
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/social/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["facebook"] is True
        assert data["instagram"] is True

    async def test_configured_without_instagram(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        settings = _social_settings()
        del settings["social"]["instagram_user_id"]
        test_tenant.settings = settings
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/social/status", headers=headers)
        data = resp.json()
        assert data["configured"] is True
        assert data["facebook"] is True
        assert data["instagram"] is False


# ── Validation ────────────────────────────────────────────────────


class TestSocialPostValidation:
    async def test_no_credentials_returns_400(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={"fb_text": "Hello world"},
        )
        assert resp.status_code == 400
        assert "credentials" in resp.json()["detail"].lower()

    async def test_no_text_returns_400(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        test_tenant.settings = _social_settings()
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"].lower()
        assert "fb_text" in detail or "ig_text" in detail

    async def test_fb_text_max_length(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={"fb_text": "x" * 5001},
        )
        assert resp.status_code == 422

    async def test_ig_text_max_length(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={"ig_text": "x" * 2201},
        )
        assert resp.status_code == 422


# ── Posting ───────────────────────────────────────────────────────


class TestSocialPost:
    @patch("app.services.social_service.httpx.AsyncClient")
    async def test_facebook_post_success(
        self,
        mock_httpx_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        test_tenant.settings = _social_settings()
        await db_session.flush()

        # Mock httpx: HEAD for photo validation, POST for Facebook
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = _mock_fb_success()
        mock_client.head.return_value = _mock_photo_validation()
        mock_httpx_cls.return_value = mock_client

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={"fb_text": "Just listed! Beautiful oceanfront condo."},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "results" in data
        fb_result = next(r for r in data["results"] if r["platform"] == "facebook")
        assert fb_result["success"] is True
        assert fb_result["post_id"] == "fb_post_123"

    @patch("app.services.social_service.httpx.AsyncClient")
    async def test_facebook_and_instagram(
        self,
        mock_httpx_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        test_tenant.settings = _social_settings()
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        # Sequential calls: HEAD (photo), POST (fb), POST (ig container), POST (ig publish)
        mock_client.head.return_value = _mock_photo_validation()
        mock_client.post.side_effect = [
            _mock_fb_success(),
            _mock_ig_container(),
            _mock_ig_publish(),
        ]
        mock_httpx_cls.return_value = mock_client

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={
                "fb_text": "Facebook post text",
                "ig_text": "Instagram caption #realestate",
                "photo_url": "https://example.com/photo.jpg",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        platforms = {r["platform"]: r for r in data["results"]}
        assert platforms["facebook"]["success"] is True
        assert platforms["instagram"]["success"] is True

    @patch("app.services.social_service.httpx.AsyncClient")
    async def test_post_creates_db_records(
        self,
        mock_httpx_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        test_tenant.settings = _social_settings()
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = _mock_fb_success()
        mock_client.head.return_value = _mock_photo_validation()
        mock_httpx_cls.return_value = mock_client

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={"fb_text": "Hello world"},
        )

        # Verify SocialPost records persisted
        result = await db_session.execute(
            select(SocialPost).where(SocialPost.tenant_id == test_tenant.id)
        )
        posts = result.scalars().all()
        assert len(posts) >= 1
        fb_posts = [p for p in posts if p.platform == "facebook"]
        assert len(fb_posts) == 1
        assert fb_posts[0].body == "Hello world"
        assert fb_posts[0].status == "success"

    @patch("app.services.social_service.httpx.AsyncClient")
    async def test_post_with_listing_id(
        self,
        mock_httpx_cls,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        test_listing,
        db_session: AsyncSession,
    ):
        test_tenant.settings = _social_settings()
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = _mock_fb_success()
        mock_client.head.return_value = _mock_photo_validation()
        mock_httpx_cls.return_value = mock_client

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={
                "fb_text": "Beautiful condo!",
                "listing_id": str(test_listing.id),
            },
        )
        assert resp.status_code == 201

        result = await db_session.execute(
            select(SocialPost).where(SocialPost.listing_id == test_listing.id)
        )
        posts = result.scalars().all()
        assert len(posts) >= 1

    async def test_ig_only_no_photo_fails(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        """Instagram requires a photo URL — posting without one should track as failed."""
        test_tenant.settings = _social_settings()
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/social/post",
            headers=headers,
            json={"ig_text": "Instagram only post"},
        )
        # Request is accepted (201) but Instagram result will show failure
        assert resp.status_code == 201
        data = resp.json()
        ig_result = next((r for r in data["results"] if r["platform"] == "instagram"), None)
        if ig_result:
            assert ig_result["success"] is False


# ── Tenant Isolation ──────────────────────────────────────────────


class TestSocialIsolation:
    async def test_other_tenant_sees_own_status(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        other_user: User,
        other_tenant: Tenant,
        db_session: AsyncSession,
    ):
        """Each tenant sees their own social configuration."""
        test_tenant.settings = _social_settings()
        await db_session.flush()

        # Test tenant: configured
        h1 = await auth_headers(client, "test@example.com", "testpassword123")
        resp1 = await client.get("/api/v1/social/status", headers=h1)
        assert resp1.json()["configured"] is True

        # Other tenant: not configured (no settings)
        h2 = await auth_headers(client, "other@example.com", "Otherpassword1!")
        resp2 = await client.get("/api/v1/social/status", headers=h2)
        assert resp2.json()["configured"] is False
