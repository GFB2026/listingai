"""Tests for admin API endpoints."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.content import Content
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


class TestAdminStats:
    async def test_stats_returns_counts(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        test_listing: Listing,
        test_content: Content,
    ):
        """Admin gets correct counts for users, listings, and content."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] == 1
        assert data["total_listings"] == 1
        assert data["total_content"] == 1

    async def test_stats_empty_tenant(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant,
    ):
        """Admin with no listings or content gets zeros."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] == 1
        assert data["total_listings"] == 0
        assert data["total_content"] == 0

    async def test_stats_agent_forbidden(
        self, client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession,
    ):
        """Agent role cannot access admin stats."""
        agent = User(
            tenant_id=test_tenant.id,
            email="agent@example.com",
            password_hash=hash_password("Agentpass123!"),
            full_name="Agent Smith",
            role="agent",
        )
        db_session.add(agent)
        await db_session.flush()

        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 403

    async def test_stats_unauthorized(self, client: AsyncClient):
        """Unauthenticated request is rejected."""
        resp = await client.get("/api/v1/admin/stats")
        assert resp.status_code in (401, 403)

    async def test_stats_cross_tenant_isolation(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        other_tenant: Tenant,
        other_user: User,
        db_session: AsyncSession,
    ):
        """Admin only sees their own tenant's counts, not other tenants."""
        # Create a listing in the other tenant
        other_listing = Listing(
            tenant_id=other_tenant.id,
            address_full="200 Beach Rd",
            address_street="200 Beach Rd",
            address_city="Miami",
            address_state="FL",
            address_zip="33139",
            price=900000,
            bedrooms=2,
            bathrooms=1,
            sqft=1200,
            property_type="condo",
            status="active",
        )
        db_session.add(other_listing)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/admin/stats", headers=headers)
        data = resp.json()
        # Should NOT see the other tenant's listing
        assert data["total_listings"] == 0
