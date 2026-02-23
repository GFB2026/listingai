"""Tests for authentication flows: register, login, refresh, logout, token blacklisting."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import User


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "Secure@pass123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)


class TestJWTTokens:
    def test_create_and_decode_access_token(self):
        data = {"sub": "user-123", "tenant_id": "tenant-456", "role": "admin"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_create_and_decode_refresh_token(self):
        data = {"sub": "user-123", "tenant_id": "tenant-456"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        assert decode_token("invalid.token.here") is None

    def test_decode_empty_token(self):
        assert decode_token("") is None


class TestRegisterEndpoint:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@galtocean.com",
                "password": "Secure@pass123",
                "full_name": "New User",
                "brokerage_name": "New Brokerage",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # Cookies should also be set
        assert "access_token" in response.cookies or "set-cookie" in response.headers

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "Secure@pass123",
                "full_name": "Duplicate User",
                "brokerage_name": "Another Brokerage",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "short",
                "full_name": "Weak User",
                "brokerage_name": "Weak Brokerage",
            },
        )
        assert response.status_code == 422  # Pydantic validation (min_length=8)

    @pytest.mark.asyncio
    async def test_register_no_uppercase(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "noupper@example.com",
                "password": "alllowercase1!",
                "full_name": "No Upper",
                "brokerage_name": "Test",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_no_special_char(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "nospecial@example.com",
                "password": "NoSpecial123",
                "full_name": "No Special",
                "brokerage_name": "Test",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "Secure@pass123",
                "full_name": "Bad Email User",
                "brokerage_name": "Bad Brokerage",
            },
        )
        assert response.status_code == 422


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever123"},
        )
        assert response.status_code == 401


class TestMeEndpoint:
    @pytest.mark.asyncio
    async def test_me_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        # No token → 401 or 403
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_me_with_bearer_token(
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
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_me_with_expired_token(self, client: AsyncClient):
        # A garbage token should fail
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer expired.token.here"},
        )
        assert response.status_code == 401


class TestRefreshEndpoint:
    @pytest.mark.asyncio
    async def test_refresh_with_body(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        refresh = create_refresh_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id)}
        )
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        # An access token is NOT a valid refresh token
        access = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_no_token(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 401


class TestRegisterDuplicateSlug:
    @pytest.mark.asyncio
    async def test_register_duplicate_slug(self, client: AsyncClient):
        """Two registrations with the same brokerage_name produces a slug conflict."""
        payload = {
            "email": "first@example.com",
            "password": "Secure@pass123",
            "full_name": "First",
            "brokerage_name": "Dup Brokerage",
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        # Clear cookies to avoid CSRF middleware blocking the second request
        client.cookies.clear()

        payload2 = {**payload, "email": "second@example.com"}
        resp2 = await client.post("/api/v1/auth/register", json=payload2)
        assert resp2.status_code == 400
        assert "slug already taken" in resp2.json()["detail"]


class TestLoginInactiveUser:
    @pytest.mark.asyncio
    async def test_inactive_user(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        test_user.is_active = False
        db_session.add(test_user)
        await db_session.flush()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()


class TestRefreshViaCookie:
    @pytest.mark.asyncio
    async def test_refresh_via_cookie(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """Refresh token from cookie should work."""
        refresh = create_refresh_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id)}
        )
        client.cookies.set("refresh_token", refresh)
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_inactive_user(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, test_tenant: Tenant
    ):
        """Refresh should fail for inactive user."""
        test_user.is_active = False
        db_session.add(test_user)
        await db_session.flush()

        refresh = create_refresh_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id)}
        )
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["detail"] == "Logged out"

    @pytest.mark.asyncio
    async def test_logout_with_bearer(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """Logout via Bearer header (no cookies = CSRF skipped)."""
        access = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert response.status_code == 200
        assert response.json()["detail"] == "Logged out"

    @pytest.mark.asyncio
    async def test_logout_blacklists_cookie_tokens(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """Logout with access_token and refresh_token cookies should blacklist both."""
        access = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )
        refresh = create_refresh_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id)}
        )
        # Set cookies + CSRF token for the request
        client.cookies.set("access_token", access)
        client.cookies.set("refresh_token", refresh)
        csrf_token = "test-csrf-token"
        client.cookies.set("csrf_token", csrf_token)

        with patch("app.api.v1.auth.blacklist_token", new_callable=AsyncMock) as mock_blacklist:
            response = await client.post(
                "/api/v1/auth/logout",
                headers={"x-csrf-token": csrf_token},
            )

        assert response.status_code == 200
        assert response.json()["detail"] == "Logged out"
        # Both tokens should have been blacklisted
        assert mock_blacklist.call_count == 2
