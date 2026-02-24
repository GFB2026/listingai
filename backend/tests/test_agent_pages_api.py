"""Tests for agent page API endpoints: list, create, update, delete."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.agent_page import AgentPage
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


# ── Fixtures ──────────────────────────────────────────────────────


async def _create_agent_user(db: AsyncSession, tenant: Tenant) -> User:
    """Create an agent-role user in the given tenant."""
    user = User(
        tenant_id=tenant.id,
        email="agent@example.com",
        password_hash=hash_password("Agentpass123!"),
        full_name="Agent Smith",
        role="agent",
    )
    db.add(user)
    await db.flush()
    return user


async def _create_agent_page(
    db: AsyncSession, tenant: Tenant, user: User, slug: str = "jane-agent",
) -> AgentPage:
    page = AgentPage(
        tenant_id=tenant.id,
        user_id=user.id,
        slug=slug,
        headline="Your Dream Home Awaits",
        bio="Top-producing agent specializing in luxury condos.",
        phone="555-0100",
        email_display="jane@realty.com",
        theme={},
    )
    db.add(page)
    await db.flush()
    return page


# ── List ──────────────────────────────────────────────────────────


class TestListAgentPages:
    async def test_list_empty(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/agent-pages", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_pages"] == []
        assert data["total"] == 0

    async def test_list_with_page(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _create_agent_page(db_session, test_tenant, test_user)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/agent-pages", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["agent_pages"][0]["slug"] == "jane-agent"
        assert data["agent_pages"][0]["id"] == str(page.id)

    async def test_list_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/agent-pages")
        assert resp.status_code in (401, 403)

    async def test_list_agent_role_forbidden(
        self, client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession,
    ):
        agent = await _create_agent_user(db_session, test_tenant)
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.get("/api/v1/agent-pages", headers=headers)
        assert resp.status_code == 403


# ── Create ────────────────────────────────────────────────────────


class TestCreateAgentPage:
    async def test_create_page(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant,
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/agent-pages",
            headers=headers,
            json={
                "user_id": str(test_user.id),
                "slug": "test-agent",
                "headline": "Welcome!",
                "bio": "Experienced agent",
                "phone": "555-0123",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["slug"] == "test-agent"
        assert data["headline"] == "Welcome!"
        assert data["is_active"] is True

    async def test_create_duplicate_slug(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        await _create_agent_page(db_session, test_tenant, test_user, slug="taken-slug")
        # Create a second user to avoid the "user already has page" error
        user2 = User(
            tenant_id=test_tenant.id,
            email="user2@example.com",
            password_hash=hash_password("User2pass123!"),
            full_name="User Two",
            role="agent",
        )
        db_session.add(user2)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/agent-pages",
            headers=headers,
            json={"user_id": str(user2.id), "slug": "taken-slug"},
        )
        assert resp.status_code == 400
        assert "Slug already in use" in resp.json()["detail"]

    async def test_create_user_already_has_page(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        await _create_agent_page(db_session, test_tenant, test_user)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/agent-pages",
            headers=headers,
            json={"user_id": str(test_user.id), "slug": "another-slug"},
        )
        assert resp.status_code == 400
        assert "already has an agent page" in resp.json()["detail"]

    async def test_create_user_not_in_tenant(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant,
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/agent-pages",
            headers=headers,
            json={"user_id": str(uuid.uuid4()), "slug": "ghost-agent"},
        )
        assert resp.status_code == 400
        assert "User not found" in resp.json()["detail"]

    async def test_create_invalid_slug(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant,
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/agent-pages",
            headers=headers,
            json={"user_id": str(test_user.id), "slug": "INVALID SLUG!"},
        )
        assert resp.status_code == 422

    async def test_create_missing_slug(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant,
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/agent-pages",
            headers=headers,
            json={"user_id": str(test_user.id)},
        )
        assert resp.status_code == 422


# ── Update ────────────────────────────────────────────────────────


class TestUpdateAgentPage:
    async def test_update_page(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _create_agent_page(db_session, test_tenant, test_user)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/agent-pages/{page.id}",
            headers=headers,
            json={"headline": "Updated Headline", "bio": "Updated bio"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["headline"] == "Updated Headline"
        assert data["bio"] == "Updated bio"

    async def test_update_slug(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _create_agent_page(db_session, test_tenant, test_user)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/agent-pages/{page.id}",
            headers=headers,
            json={"slug": "new-slug"},
        )
        assert resp.status_code == 200
        assert resp.json()["slug"] == "new-slug"

    async def test_update_slug_duplicate(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _create_agent_page(db_session, test_tenant, test_user, slug="page-one")
        # Create second user + page
        user2 = User(
            tenant_id=test_tenant.id,
            email="user2@example.com",
            password_hash=hash_password("User2pass123!"),
            full_name="User Two",
            role="agent",
        )
        db_session.add(user2)
        await db_session.flush()
        page2 = await _create_agent_page(db_session, test_tenant, user2, slug="page-two")

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/agent-pages/{page2.id}",
            headers=headers,
            json={"slug": "page-one"},
        )
        assert resp.status_code == 400
        assert "Slug already in use" in resp.json()["detail"]

    async def test_update_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/agent-pages/{uuid.uuid4()}",
            headers=headers,
            json={"headline": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_agent_can_update_own_page(
        self, client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession,
    ):
        agent = await _create_agent_user(db_session, test_tenant)
        page = await _create_agent_page(db_session, test_tenant, agent, slug="agent-page")
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.patch(
            f"/api/v1/agent-pages/{page.id}",
            headers=headers,
            json={"headline": "My Page"},
        )
        assert resp.status_code == 200

    async def test_agent_cannot_update_other_page(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        # Create page owned by test_user (admin)
        page = await _create_agent_page(db_session, test_tenant, test_user, slug="admin-page")
        # Login as agent
        agent = await _create_agent_user(db_session, test_tenant)
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.patch(
            f"/api/v1/agent-pages/{page.id}",
            headers=headers,
            json={"headline": "Hijacked"},
        )
        assert resp.status_code == 403


# ── Delete (soft) ─────────────────────────────────────────────────


class TestDeleteAgentPage:
    async def test_delete_page(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _create_agent_page(db_session, test_tenant, test_user)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/agent-pages/{page.id}", headers=headers)
        assert resp.status_code == 204

        # Verify it's deactivated, not hard-deleted
        list_resp = await client.get("/api/v1/agent-pages", headers=headers)
        pages = list_resp.json()["agent_pages"]
        assert len(pages) == 1
        assert pages[0]["is_active"] is False

    async def test_delete_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/agent-pages/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_delete_agent_role_forbidden(
        self, client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession,
    ):
        agent = await _create_agent_user(db_session, test_tenant)
        page = await _create_agent_page(db_session, test_tenant, agent, slug="agent-pg")
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.delete(f"/api/v1/agent-pages/{page.id}", headers=headers)
        assert resp.status_code == 403
