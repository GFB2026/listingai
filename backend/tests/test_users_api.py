"""Tests for user management API endpoints: list, create, update, delete, role checks."""
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


class TestListUsers:
    async def test_list_users(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        emails = [u["email"] for u in data["users"]]
        assert "test@example.com" in emails


class TestCreateUser:
    async def test_create_user(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """Admin creates an agent user."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "agent@example.com",
                "password": "Agentpass1!",
                "full_name": "Agent Smith",
                "role": "agent",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "agent@example.com"
        assert data["role"] == "agent"

    async def test_create_user_duplicate_email(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "test@example.com",
                "password": "Duplicate1!",
                "full_name": "Dup User",
                "role": "agent",
            },
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    async def test_create_user_role_required(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession
    ):
        """Agent role cannot create users (requires admin/broker)."""
        # Create an agent user first
        agent = User(
            tenant_id=test_tenant.id,
            email="lowagent@example.com",
            password_hash=hash_password("Agentpass1!"),
            full_name="Low Agent",
            role="agent",
        )
        db_session.add(agent)
        await db_session.flush()

        headers = await auth_headers(client, "lowagent@example.com", "Agentpass1!")
        resp = await client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "newuser@example.com",
                "password": "Newpass1!",
                "full_name": "New User",
                "role": "agent",
            },
        )
        assert resp.status_code == 403


class TestUpdateUser:
    async def test_update_user(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession
    ):
        # Create target user
        target = User(
            tenant_id=test_tenant.id,
            email="target@example.com",
            password_hash=hash_password("Targetpass1!"),
            full_name="Target User",
            role="agent",
        )
        db_session.add(target)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/users/{target.id}",
            headers=headers,
            json={"full_name": "Updated Name", "role": "broker"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Updated Name"
        assert data["role"] == "broker"

    async def test_update_user_not_found(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/users/{uuid.uuid4()}",
            headers=headers,
            json={"full_name": "Ghost"},
        )
        assert resp.status_code == 404


class TestDeleteUser:
    async def test_delete_user(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession
    ):
        # Create a user to delete
        victim = User(
            tenant_id=test_tenant.id,
            email="victim@example.com",
            password_hash=hash_password("Victimpass1!"),
            full_name="Victim User",
            role="agent",
        )
        db_session.add(victim)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/users/{victim.id}", headers=headers)
        assert resp.status_code == 204

    async def test_delete_self_prevented(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/users/{test_user.id}", headers=headers)
        assert resp.status_code == 400
        assert "Cannot delete your own" in resp.json()["detail"]

    async def test_delete_user_not_found(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/users/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404


class TestAgentCannotManageUsers:
    async def test_agent_cannot_manage_users(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession
    ):
        agent = User(
            tenant_id=test_tenant.id,
            email="restrictedagent@example.com",
            password_hash=hash_password("Agentpass1!"),
            full_name="Restricted Agent",
            role="agent",
        )
        db_session.add(agent)
        await db_session.flush()

        agent_headers = await auth_headers(client, "restrictedagent@example.com", "Agentpass1!")

        # Cannot create
        resp = await client.post(
            "/api/v1/users",
            headers=agent_headers,
            json={
                "email": "forbidden@example.com",
                "password": "Forbidden1!",
                "full_name": "Forbidden",
                "role": "agent",
            },
        )
        assert resp.status_code == 403

        # Cannot delete
        resp2 = await client.delete(
            f"/api/v1/users/{test_user.id}", headers=agent_headers
        )
        assert resp2.status_code == 403
