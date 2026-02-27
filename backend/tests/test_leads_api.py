"""Tests for authenticated lead management API endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.agent_page import AgentPage
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


# ── Helpers ───────────────────────────────────────────────────────


async def _agent_user(db: AsyncSession, tenant: Tenant) -> User:
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


async def _agent_page(db: AsyncSession, tenant: Tenant, user: User) -> AgentPage:
    page = AgentPage(
        tenant_id=tenant.id,
        user_id=user.id,
        slug="agent-smith",
        headline="Test",
        theme={},
    )
    db.add(page)
    await db.flush()
    return page


async def _lead(
    db: AsyncSession,
    tenant: Tenant,
    agent: User,
    page: AgentPage,
    *,
    first_name: str = "John",
    pipeline_status: str = "new",
    utm_source: str | None = None,
) -> Lead:
    lead = Lead(
        tenant_id=tenant.id,
        agent_page_id=page.id,
        agent_id=agent.id,
        first_name=first_name,
        last_name="Doe",
        email="john@example.com",
        phone="555-0001",
        pipeline_status=pipeline_status,
        utm_source=utm_source,
    )
    db.add(lead)
    await db.flush()
    return lead


# ── List ──────────────────────────────────────────────────────────


class TestListLeads:
    async def test_list_leads_empty(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant,
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/leads", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["leads"] == []
        assert data["total"] == 0

    async def test_list_leads_with_data(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/leads", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["leads"][0]["first_name"] == "John"
        assert data["leads"][0]["agent_name"] == "Test User"

    async def test_list_leads_filter_status(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        await _lead(db_session, test_tenant, test_user, page, pipeline_status="new")
        await _lead(
            db_session, test_tenant, test_user, page,
            first_name="Jane", pipeline_status="contacted",
        )
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            "/api/v1/leads", headers=headers, params={"pipeline_status": "contacted"},
        )
        data = resp.json()
        assert data["total"] == 1
        assert data["leads"][0]["first_name"] == "Jane"

    async def test_list_leads_filter_utm_source(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        await _lead(db_session, test_tenant, test_user, page, utm_source="google")
        await _lead(
            db_session, test_tenant, test_user, page,
            first_name="Jane", utm_source="facebook",
        )
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            "/api/v1/leads", headers=headers, params={"utm_source": "google"},
        )
        data = resp.json()
        assert data["total"] == 1
        assert data["leads"][0]["utm_source"] == "google"

    async def test_list_leads_pagination(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        for i in range(5):
            await _lead(
                db_session, test_tenant, test_user, page, first_name=f"Lead{i}",
            )
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            "/api/v1/leads", headers=headers, params={"page": 1, "page_size": 2},
        )
        data = resp.json()
        assert data["total"] == 5
        assert len(data["leads"]) == 2

    async def test_agent_sees_only_own_leads(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        # Admin creates a page + lead assigned to admin
        admin_page = await _agent_page(db_session, test_tenant, test_user)
        await _lead(db_session, test_tenant, test_user, admin_page, first_name="AdminLead")

        # Agent user with own lead
        agent = await _agent_user(db_session, test_tenant)
        agent_pg = AgentPage(
            tenant_id=test_tenant.id, user_id=agent.id, slug="agent-pg", theme={},
        )
        db_session.add(agent_pg)
        await db_session.flush()
        await _lead(db_session, test_tenant, agent, agent_pg, first_name="AgentLead")

        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.get("/api/v1/leads", headers=headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["leads"][0]["first_name"] == "AgentLead"

    async def test_list_leads_filter_by_agent_id(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        """Admin can filter leads by agent_id parameter."""
        page = await _agent_page(db_session, test_tenant, test_user)
        await _lead(db_session, test_tenant, test_user, page, first_name="AdminLead")

        # Create agent with their own lead
        agent = await _agent_user(db_session, test_tenant)
        agent_pg = AgentPage(
            tenant_id=test_tenant.id, user_id=agent.id, slug="filter-agent", theme={},
        )
        db_session.add(agent_pg)
        await db_session.flush()
        await _lead(db_session, test_tenant, agent, agent_pg, first_name="AgentLead")

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            "/api/v1/leads", headers=headers, params={"agent_id": str(agent.id)},
        )
        data = resp.json()
        assert data["total"] == 1
        assert data["leads"][0]["first_name"] == "AgentLead"

    async def test_list_leads_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/leads")
        assert resp.status_code in (401, 403)


# ── Get Detail ────────────────────────────────────────────────────


class TestGetLead:
    async def test_get_lead(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(f"/api/v1/leads/{lead.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["lead"]["first_name"] == "John"
        assert isinstance(data["activities"], list)

    async def test_get_lead_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(f"/api/v1/leads/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_agent_cannot_get_others_lead(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        # Lead owned by admin
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        # Login as agent
        await _agent_user(db_session, test_tenant)
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.get(f"/api/v1/leads/{lead.id}", headers=headers)
        assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────


class TestUpdateLead:
    async def test_update_status(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/leads/{lead.id}",
            headers=headers,
            json={"pipeline_status": "contacted"},
        )
        assert resp.status_code == 200
        assert resp.json()["pipeline_status"] == "contacted"

    async def test_update_to_closed_sets_closed_at(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/leads/{lead.id}",
            headers=headers,
            json={"pipeline_status": "closed", "closed_value": 500000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_status"] == "closed"
        assert data["closed_at"] is not None

    async def test_update_contact_info(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/leads/{lead.id}",
            headers=headers,
            json={"first_name": "Johnny", "phone": "555-9999"},
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Johnny"
        assert resp.json()["phone"] == "555-9999"

    async def test_update_all_contact_fields(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        """Cover last_name, email, and property_interest update paths."""
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/leads/{lead.id}",
            headers=headers,
            json={
                "last_name": "Smith",
                "email": "updated@example.com",
                "property_interest": "3BR condo near beach",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["last_name"] == "Smith"
        assert data["email"] == "updated@example.com"
        assert data["property_interest"] == "3BR condo near beach"

    async def test_update_invalid_status(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/leads/{lead.id}",
            headers=headers,
            json={"pipeline_status": "nonexistent"},
        )
        assert resp.status_code == 400

    async def test_update_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/leads/{uuid.uuid4()}",
            headers=headers,
            json={"pipeline_status": "contacted"},
        )
        assert resp.status_code == 404

    async def test_agent_cannot_update_others_lead(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        await _agent_user(db_session, test_tenant)
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.patch(
            f"/api/v1/leads/{lead.id}",
            headers=headers,
            json={"pipeline_status": "contacted"},
        )
        assert resp.status_code == 403


# ── Delete ────────────────────────────────────────────────────────


class TestDeleteLead:
    async def test_delete_lead(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/leads/{lead.id}", headers=headers)
        assert resp.status_code == 204

        # Verify gone
        list_resp = await client.get("/api/v1/leads", headers=headers)
        assert list_resp.json()["total"] == 0

    async def test_delete_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/leads/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_delete_agent_forbidden(
        self, client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession,
    ):
        agent = await _agent_user(db_session, test_tenant)
        page = await _agent_page(db_session, test_tenant, agent)
        lead = await _lead(db_session, test_tenant, agent, page)
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.delete(f"/api/v1/leads/{lead.id}", headers=headers)
        assert resp.status_code == 403


# ── Activities ────────────────────────────────────────────────────


class TestLeadActivities:
    async def test_add_note(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            f"/api/v1/leads/{lead.id}/activities",
            headers=headers,
            json={"activity_type": "note", "note": "Called client, no answer."},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["activity_type"] == "note"
        assert data["note"] == "Called client, no answer."
        assert data["user_name"] == "Test User"

    async def test_add_activity_lead_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            f"/api/v1/leads/{uuid.uuid4()}/activities",
            headers=headers,
            json={"activity_type": "note"},
        )
        assert resp.status_code == 404

    async def test_agent_cannot_add_activity_to_others_lead(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        await _agent_user(db_session, test_tenant)
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.post(
            f"/api/v1/leads/{lead.id}/activities",
            headers=headers,
            json={"activity_type": "note", "note": "Hijacked"},
        )
        assert resp.status_code == 403

    async def test_activities_appear_in_detail(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        lead = await _lead(db_session, test_tenant, test_user, page)
        # Add an activity directly
        activity = LeadActivity(
            lead_id=lead.id,
            user_id=test_user.id,
            activity_type="note",
            note="Test note",
        )
        db_session.add(activity)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(f"/api/v1/leads/{lead.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["activities"]) == 1
        assert data["activities"][0]["note"] == "Test note"


# ── Analytics ─────────────────────────────────────────────────────


class TestLeadAnalytics:
    async def test_summary(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        await _lead(db_session, test_tenant, test_user, page, pipeline_status="new")
        await _lead(
            db_session, test_tenant, test_user, page,
            first_name="Jane", pipeline_status="contacted",
        )
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/leads/analytics/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads"] == 2
        assert data["by_status"]["new"] == 1
        assert data["by_status"]["contacted"] == 1

    async def test_funnel(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession,
    ):
        page = await _agent_page(db_session, test_tenant, test_user)
        for _ in range(3):
            await _lead(db_session, test_tenant, test_user, page, pipeline_status="new")
        await _lead(
            db_session, test_tenant, test_user, page,
            first_name="Jane", pipeline_status="contacted",
        )
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/leads/analytics/funnel", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        funnel = {step["status"]: step for step in data["funnel"]}
        assert funnel["new"]["count"] == 3
        assert funnel["contacted"]["count"] == 1
        assert funnel["new"]["percentage"] == 75.0

    async def test_analytics_agent_forbidden(
        self, client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession,
    ):
        await _agent_user(db_session, test_tenant)
        headers = await auth_headers(client, "agent@example.com", "Agentpass123!")
        resp = await client.get("/api/v1/leads/analytics/summary", headers=headers)
        assert resp.status_code == 403

        resp = await client.get("/api/v1/leads/analytics/funnel", headers=headers)
        assert resp.status_code == 403
