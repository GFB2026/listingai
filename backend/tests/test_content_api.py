import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.tenant import Tenant
from app.models.user import User


class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@galtocean.com",
                "password": "securepassword123",
                "full_name": "Admin User",
                "brokerage_name": "Galt Ocean Realty",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_invalid(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrong",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403  # No bearer token

    @pytest.mark.asyncio
    async def test_me_authorized(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        token = create_access_token(
            data={
                "sub": str(test_user.id),
                "tenant_id": str(test_tenant.id),
                "role": "admin",
            }
        )
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
