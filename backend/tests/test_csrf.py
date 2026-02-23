"""Tests for CSRF middleware — double-submit cookie pattern."""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.tenant import Tenant
from app.models.user import User


class TestCSRFMiddleware:
    @pytest.mark.asyncio
    async def test_csrf_rejected_when_cookie_auth_without_csrf_header(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """POST with access_token cookie but missing CSRF header should be rejected."""
        access = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )
        # Set access_token cookie but NO csrf_token
        client.cookies.set("access_token", access)
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 403
        assert "csrf" in response.json().get("error", "").lower()

    @pytest.mark.asyncio
    async def test_csrf_rejected_when_csrf_header_mismatch(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """POST with mismatched CSRF cookie and header should be rejected."""
        access = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )
        client.cookies.set("access_token", access)
        client.cookies.set("csrf_token", "cookie-value")
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"x-csrf-token": "different-value"},
        )
        assert response.status_code == 403
        assert "csrf" in response.json().get("error", "").lower()

    @pytest.mark.asyncio
    async def test_csrf_passes_when_tokens_match(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """POST with matching CSRF cookie and header should pass."""
        access = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )
        csrf_token = "valid-csrf-token"
        client.cookies.set("access_token", access)
        client.cookies.set("csrf_token", csrf_token)
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"x-csrf-token": csrf_token},
        )
        assert response.status_code == 200
        assert response.json()["detail"] == "Logged out"

    @pytest.mark.asyncio
    async def test_csrf_skipped_for_bearer_auth(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """Bearer-only auth (no cookies) should skip CSRF validation."""
        access = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_csrf_cookie_set_on_get(self, client: AsyncClient):
        """GET requests should set csrf_token cookie if not present."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        # CSRF cookie should be set on response
        cookies = {c.name: c for c in response.cookies.jar}
        assert "csrf_token" in cookies
