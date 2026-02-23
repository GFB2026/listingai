"""Tests for tenants API endpoints."""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.tenant import Tenant
from app.models.user import User


def _auth_token(user: User, tenant: Tenant) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


class TestGetCurrentTenant:
    @pytest.mark.asyncio
    async def test_get_current(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.get("/api/v1/tenants/current", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Brokerage"
        assert data["slug"] == "test-brokerage"
        assert data["plan"] == "professional"

    @pytest.mark.asyncio
    async def test_get_current_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/tenants/current")
        assert response.status_code in (401, 403)


class TestUpdateCurrentTenant:
    @pytest.mark.asyncio
    async def test_update_name(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.patch(
            "/api/v1/tenants/current",
            headers=headers,
            json={"name": "Updated Brokerage"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Brokerage"

    @pytest.mark.asyncio
    async def test_update_settings(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.patch(
            "/api/v1/tenants/current",
            headers=headers,
            json={"settings": {"theme": "dark"}},
        )
        assert response.status_code == 200
        assert response.json()["settings"] == {"theme": "dark"}

    @pytest.mark.asyncio
    async def test_update_requires_admin_or_broker(
        self, client: AsyncClient, test_tenant: Tenant, db_session
    ):
        """A non-admin/broker role should be rejected."""
        from app.core.security import hash_password
        from app.models.user import User

        agent_user = User(
            tenant_id=test_tenant.id,
            email="agent@example.com",
            password_hash=hash_password("Agentpass1!"),
            full_name="Agent User",
            role="agent",
        )
        db_session.add(agent_user)
        await db_session.flush()

        token = create_access_token(
            data={
                "sub": str(agent_user.id),
                "tenant_id": str(test_tenant.id),
                "role": "agent",
            }
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            "/api/v1/tenants/current",
            headers=headers,
            json={"name": "Nope"},
        )
        assert response.status_code == 403
