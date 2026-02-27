"""Tests for MLS connections API endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.mls_connection import MLSConnection
from app.models.tenant import Tenant
from app.models.user import User


def _make_connection(tenant_id) -> MLSConnection:
    """Create an MLSConnection with raw bytes for encrypted fields."""
    return MLSConnection(
        tenant_id=tenant_id,
        provider="trestle",
        name="Test MLS",
        base_url="https://api-trestle.corelogic.com",
        client_id_encrypted=b"encrypted_client_id",
        client_secret_encrypted=b"encrypted_client_secret",
        sync_enabled=True,
    )


def _auth_token(user: User, tenant: Tenant) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


class TestListConnections:
    @pytest.mark.asyncio
    async def test_list_empty(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.get("/api/v1/mls-connections", headers=headers)
        assert response.status_code == 200
        assert response.json()["connections"] == []

    @pytest.mark.asyncio
    async def test_list_with_connections(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        headers = _auth_token(test_user, test_tenant)
        response = await client.get("/api/v1/mls-connections", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["connections"]) == 1
        assert data["connections"][0]["provider"] == "trestle"


class TestCreateConnection:
    @pytest.mark.asyncio
    @patch("app.api.v1.mls_connections.encrypt_value", return_value=b"encrypted")
    async def test_create(
        self,
        mock_encrypt,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.post(
            "/api/v1/mls-connections",
            headers=headers,
            json={
                "provider": "trestle",
                "name": "My MLS",
                "base_url": "https://api-trestle.corelogic.com",
                "client_id": "test_id",
                "client_secret": "test_secret",
                "sync_enabled": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["provider"] == "trestle"
        assert data["name"] == "My MLS"
        assert mock_encrypt.call_count == 2


class TestUpdateConnection:
    @pytest.mark.asyncio
    @patch("app.api.v1.mls_connections.encrypt_value", return_value=b"re-encrypted")
    async def test_update(
        self,
        mock_encrypt,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        headers = _auth_token(test_user, test_tenant)
        response = await client.patch(
            f"/api/v1/mls-connections/{conn.id}",
            headers=headers,
            json={"name": "Updated MLS", "sync_enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated MLS"
        assert response.json()["sync_enabled"] is False

    @pytest.mark.asyncio
    async def test_update_not_found(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.patch(
            "/api/v1/mls-connections/00000000-0000-0000-0000-000000000000",
            headers=headers,
            json={"name": "nope"},
        )
        assert response.status_code == 404


class TestDeleteConnection:
    @pytest.mark.asyncio
    async def test_delete(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        headers = _auth_token(test_user, test_tenant)
        response = await client.delete(
            f"/api/v1/mls-connections/{conn.id}", headers=headers
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.delete(
            "/api/v1/mls-connections/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert response.status_code == 404


class TestTestConnection:
    @pytest.mark.asyncio
    async def test_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock()
        mock_client.get_properties = AsyncMock(
            return_value={"value": [{"ListingKey": "ABC"}]}
        )
        mock_client.close = AsyncMock()

        with patch(
            "app.api.v1.mls_connections.RESOClient.from_connection",
            return_value=mock_client,
        ):
            headers = _auth_token(test_user, test_tenant)
            response = await client.post(
                f"/api/v1/mls-connections/{conn.id}/test", headers=headers
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["property_count"] == 1

    @pytest.mark.asyncio
    async def test_failure(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(side_effect=Exception("Auth failed"))
        mock_client.close = AsyncMock()

        with patch(
            "app.api.v1.mls_connections.RESOClient.from_connection",
            return_value=mock_client,
        ):
            headers = _auth_token(test_user, test_tenant)
            response = await client.post(
                f"/api/v1/mls-connections/{conn.id}/test", headers=headers
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Auth failed" in data["message"]


class TestGetConnectionStatus:
    @pytest.mark.asyncio
    async def test_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        headers = _auth_token(test_user, test_tenant)
        response = await client.get(
            f"/api/v1/mls-connections/{conn.id}/status", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["listing_count"] == 0
        assert data["sync_enabled"] is True
