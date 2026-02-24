"""Tests for public (unauthenticated) endpoints: landing pages, lead capture, visits."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.agent_page import AgentPage
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.user import User


# ── Helpers ───────────────────────────────────────────────────────


async def _setup_public(
    db: AsyncSession,
) -> tuple[Tenant, User, AgentPage, Listing]:
    """Create tenant, user, agent page, and listing for public API tests."""
    tenant = Tenant(
        name="Test Brokerage",
        slug="test-brokerage",
        plan="professional",
        monthly_generation_limit=1000,
    )
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email="agent@test.com",
        password_hash=hash_password("Test1234!"),
        full_name="Jane Agent",
        role="agent",
    )
    db.add(user)
    await db.flush()

    page = AgentPage(
        tenant_id=tenant.id,
        user_id=user.id,
        slug="jane-agent",
        headline="Your Dream Home",
        bio="Top-producing agent.",
        phone="555-0100",
        email_display="jane@realty.com",
        theme={"primary_color": "#0066cc"},
    )
    db.add(page)
    await db.flush()

    listing = Listing(
        tenant_id=tenant.id,
        listing_agent_id=user.id,
        address_full="100 Ocean Blvd, Fort Lauderdale, FL 33308",
        address_street="100 Ocean Blvd",
        address_city="Fort Lauderdale",
        address_state="FL",
        address_zip="33308",
        price=1500000,
        bedrooms=3,
        bathrooms=2,
        sqft=2200,
        property_type="condo",
        status="active",
    )
    db.add(listing)
    await db.flush()

    return tenant, user, page, listing


# ── Agent Landing Page ────────────────────────────────────────────


class TestGetAgentPage:
    async def test_get_agent_page(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, listing = await _setup_public(db_session)
        resp = await client.get(f"/api/v1/public/pages/{tenant.slug}/{page.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"]["slug"] == "jane-agent"
        assert data["agent"]["headline"] == "Your Dream Home"
        assert data["agent"]["name"] == "Jane Agent"
        assert data["brokerage"]["name"] == "Test Brokerage"
        assert len(data["listings"]) == 1
        assert data["listings"][0]["address_full"] == "100 Ocean Blvd, Fort Lauderdale, FL 33308"
        assert data["listings"][0]["price"] == 1500000

    async def test_get_agent_page_tenant_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/public/pages/nonexistent/some-agent")
        assert resp.status_code == 404

    async def test_get_agent_page_slug_not_found(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        tenant, _, _, _ = await _setup_public(db_session)
        resp = await client.get(f"/api/v1/public/pages/{tenant.slug}/nonexistent")
        assert resp.status_code == 404

    async def test_get_inactive_page_not_found(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        tenant, user, page, _ = await _setup_public(db_session)
        page.is_active = False
        db_session.add(page)
        await db_session.flush()
        resp = await client.get(f"/api/v1/public/pages/{tenant.slug}/{page.slug}")
        assert resp.status_code == 404


# ── Listing Landing Page ──────────────────────────────────────────


class TestGetListingLanding:
    async def test_get_listing_landing(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, listing = await _setup_public(db_session)
        resp = await client.get(
            f"/api/v1/public/pages/{tenant.slug}/{page.slug}/listings/{listing.id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"]["slug"] == "jane-agent"
        assert data["listing"]["address_full"] == "100 Ocean Blvd, Fort Lauderdale, FL 33308"
        assert data["listing"]["price"] == 1500000
        assert data["listing"]["bedrooms"] == 3

    async def test_listing_not_found(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, _ = await _setup_public(db_session)
        import uuid

        resp = await client.get(
            f"/api/v1/public/pages/{tenant.slug}/{page.slug}/listings/{uuid.uuid4()}"
        )
        assert resp.status_code == 404


# ── Lead Submission ───────────────────────────────────────────────


class TestSubmitLead:
    async def test_submit_lead(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, listing = await _setup_public(db_session)
        resp = await client.post(
            "/api/v1/public/leads",
            json={
                "tenant_slug": tenant.slug,
                "agent_slug": page.slug,
                "listing_id": str(listing.id),
                "first_name": "Bob",
                "last_name": "Buyer",
                "email": "bob@example.com",
                "phone": "555-1234",
                "message": "I'm interested in this property.",
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "summer-2026",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] == "received"

    async def test_submit_lead_minimal(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, _ = await _setup_public(db_session)
        resp = await client.post(
            "/api/v1/public/leads",
            json={
                "tenant_slug": tenant.slug,
                "agent_slug": page.slug,
                "first_name": "Alice",
            },
        )
        assert resp.status_code == 201

    async def test_submit_lead_missing_first_name(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        tenant, user, page, _ = await _setup_public(db_session)
        resp = await client.post(
            "/api/v1/public/leads",
            json={
                "tenant_slug": tenant.slug,
                "agent_slug": page.slug,
            },
        )
        assert resp.status_code == 422

    async def test_submit_lead_invalid_agent(self, client: AsyncClient, db_session: AsyncSession):
        tenant, _, _, _ = await _setup_public(db_session)
        resp = await client.post(
            "/api/v1/public/leads",
            json={
                "tenant_slug": tenant.slug,
                "agent_slug": "nonexistent-agent",
                "first_name": "Bob",
            },
        )
        assert resp.status_code == 404

    async def test_submit_lead_invalid_tenant(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/public/leads",
            json={
                "tenant_slug": "nonexistent",
                "agent_slug": "any",
                "first_name": "Bob",
            },
        )
        assert resp.status_code == 404


# ── Visit Tracking ────────────────────────────────────────────────


class TestRecordVisit:
    async def test_record_visit(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, listing = await _setup_public(db_session)
        resp = await client.post(
            "/api/v1/public/visits",
            json={
                "tenant_slug": tenant.slug,
                "agent_slug": page.slug,
                "listing_id": str(listing.id),
                "session_id": "sess-abc-123",
                "utm_source": "facebook",
                "utm_medium": "social",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "ok"

    async def test_record_visit_minimal(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, _ = await _setup_public(db_session)
        resp = await client.post(
            "/api/v1/public/visits",
            json={
                "tenant_slug": tenant.slug,
                "agent_slug": page.slug,
            },
        )
        assert resp.status_code == 201

    async def test_record_visit_invalid_agent(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        tenant, _, _, _ = await _setup_public(db_session)
        resp = await client.post(
            "/api/v1/public/visits",
            json={
                "tenant_slug": tenant.slug,
                "agent_slug": "ghost",
            },
        )
        assert resp.status_code == 404


# ── Link Config ───────────────────────────────────────────────────


class TestLinkConfig:
    async def test_get_link_config(self, client: AsyncClient, db_session: AsyncSession):
        tenant, user, page, listing = await _setup_public(db_session)
        resp = await client.get(f"/api/v1/public/link-config/{tenant.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_slug"] == tenant.slug
        assert len(data["agents"]) == 1
        assert data["agents"][0]["slug"] == "jane-agent"
        assert data["agents"][0]["name"] == "Jane Agent"
        assert len(data["agents"][0]["listings"]) == 1

    async def test_link_config_tenant_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/public/link-config/nonexistent")
        assert resp.status_code == 404
