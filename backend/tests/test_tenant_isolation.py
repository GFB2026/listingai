"""Tests for multi-tenant isolation: Tenant A cannot see/modify Tenant B's data."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.brand_profile import BrandProfile
from app.models.content import Content
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


@pytest.fixture
async def tenant_a_setup(db_session: AsyncSession):
    """Set up Tenant A with user, listing, content, and brand profile."""
    tenant = Tenant(
        name="Tenant A", slug="tenant-a",
        plan="professional", monthly_generation_limit=1000,
    )
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="a@tenanta.com",
        password_hash=hash_password("Tenanta1!"),
        full_name="User A",
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()

    listing = Listing(
        tenant_id=tenant.id,
        address_full="1 A Street",
        address_city="A City",
        status="active",
        price=500000,
    )
    db_session.add(listing)
    await db_session.flush()

    content = Content(
        tenant_id=tenant.id,
        listing_id=listing.id,
        user_id=user.id,
        content_type="listing_description",
        body="Tenant A's content",
        ai_model="test",
    )
    db_session.add(content)
    await db_session.flush()

    profile = BrandProfile(
        tenant_id=tenant.id,
        name="A's Brand",
        is_default=True,
    )
    db_session.add(profile)
    await db_session.flush()

    return {
        "tenant": tenant, "user": user, "listing": listing,
        "content": content, "profile": profile,
    }


@pytest.fixture
async def tenant_b_setup(db_session: AsyncSession):
    """Set up Tenant B with user, listing, content, and brand profile."""
    tenant = Tenant(name="Tenant B", slug="tenant-b", plan="starter", monthly_generation_limit=200)
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="b@tenantb.com",
        password_hash=hash_password("Tenantb1!"),
        full_name="User B",
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()

    listing = Listing(
        tenant_id=tenant.id,
        address_full="2 B Street",
        address_city="B City",
        status="active",
        price=400000,
    )
    db_session.add(listing)
    await db_session.flush()

    content = Content(
        tenant_id=tenant.id,
        listing_id=listing.id,
        user_id=user.id,
        content_type="listing_description",
        body="Tenant B's content",
        ai_model="test",
    )
    db_session.add(content)
    await db_session.flush()

    profile = BrandProfile(
        tenant_id=tenant.id,
        name="B's Brand",
        is_default=True,
    )
    db_session.add(profile)
    await db_session.flush()

    return {
        "tenant": tenant, "user": user, "listing": listing,
        "content": content, "profile": profile,
    }


class TestListingIsolation:
    async def test_tenant_a_cannot_list_tenant_b_listings(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        resp = await client.get("/api/v1/listings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Tenant A should only see their own listing
        assert data["total"] == 1
        assert data["listings"][0]["address_full"] == "1 A Street"

    async def test_tenant_a_cannot_get_tenant_b_listing(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        b_listing_id = tenant_b_setup["listing"].id
        resp = await client.get(f"/api/v1/listings/{b_listing_id}", headers=headers)
        assert resp.status_code == 404


class TestContentIsolation:
    async def test_tenant_a_cannot_list_tenant_b_content(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        resp = await client.get("/api/v1/content", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["content"][0]["body"] == "Tenant A's content"

    async def test_tenant_a_cannot_get_tenant_b_content(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        b_content_id = tenant_b_setup["content"].id
        resp = await client.get(f"/api/v1/content/{b_content_id}", headers=headers)
        assert resp.status_code == 404

    async def test_tenant_a_cannot_delete_tenant_b_content(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        b_content_id = tenant_b_setup["content"].id
        resp = await client.delete(f"/api/v1/content/{b_content_id}", headers=headers)
        assert resp.status_code == 404


class TestBrandProfileIsolation:
    async def test_tenant_a_cannot_list_tenant_b_profiles(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        resp = await client.get("/api/v1/brand-profiles", headers=headers)
        assert resp.status_code == 200
        profiles = resp.json()
        assert len(profiles) == 1
        assert profiles[0]["name"] == "A's Brand"

    async def test_tenant_a_cannot_delete_tenant_b_profile(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        b_profile_id = tenant_b_setup["profile"].id
        resp = await client.delete(f"/api/v1/brand-profiles/{b_profile_id}", headers=headers)
        assert resp.status_code == 404


class TestUserIsolation:
    async def test_tenant_a_cannot_list_tenant_b_users(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        resp = await client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        emails = [u["email"] for u in data["users"]]
        assert "a@tenanta.com" in emails
        assert "b@tenantb.com" not in emails

    async def test_tenant_a_cannot_delete_tenant_b_user(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        b_user_id = tenant_b_setup["user"].id
        resp = await client.delete(f"/api/v1/users/{b_user_id}", headers=headers)
        assert resp.status_code == 404

    async def test_tenant_a_cannot_update_tenant_b_user(
        self, client: AsyncClient, tenant_a_setup, tenant_b_setup
    ):
        headers = await auth_headers(client, "a@tenanta.com", "Tenanta1!")
        b_user_id = tenant_b_setup["user"].id
        resp = await client.patch(
            f"/api/v1/users/{b_user_id}",
            headers=headers,
            json={"full_name": "Hacked"},
        )
        assert resp.status_code == 404
