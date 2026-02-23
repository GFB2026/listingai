"""Tests for billing/usage API endpoints."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent
from app.models.user import User
from tests.conftest import auth_headers


class TestGetUsage:
    async def test_get_usage(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/billing/usage", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "professional"
        assert data["credits_limit"] == 1000
        assert data["credits_used"] == 0
        assert data["credits_remaining"] == 1000

    async def test_get_usage_with_events(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession
    ):
        # Add some usage events for this month
        for _ in range(3):
            event = UsageEvent(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                event_type="content_generation",
                content_type="listing_description",
                credits_consumed=1,
                tokens_used=500,
            )
            db_session.add(event)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/billing/usage", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["credits_used"] == 3
        assert data["credits_remaining"] == 997

    async def test_get_usage_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/billing/usage")
        assert resp.status_code in (401, 403)


class TestSubscribe:
    async def test_subscribe_requires_admin(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession
    ):
        """Agent role cannot subscribe."""
        agent = User(
            tenant_id=test_tenant.id,
            email="billagent@example.com",
            password_hash=hash_password("Agentpass1!"),
            full_name="Bill Agent",
            role="agent",
        )
        db_session.add(agent)
        await db_session.flush()

        headers = await auth_headers(client, "billagent@example.com", "Agentpass1!")
        resp = await client.post(
            "/api/v1/billing/subscribe?price_id=price_test_123",
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_subscribe_stripe_error(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        with patch(
            "app.services.billing_service.BillingService.create_or_update_subscription",
            new_callable=AsyncMock,
            side_effect=ValueError("Payment provider error: card declined"),
        ):
            resp = await client.post(
                "/api/v1/billing/subscribe?price_id=price_test_123",
                headers=headers,
            )
        assert resp.status_code == 400
        assert "Payment provider error" in resp.json()["detail"]


class TestUsageMonthlyReset:
    async def test_usage_monthly_reset(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, db_session: AsyncSession
    ):
        """Usage from previous month doesn't count toward current month."""
        # Add usage event from last month
        last_month = datetime(2025, 12, 15, tzinfo=UTC)
        old_event = UsageEvent(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            event_type="content_generation",
            content_type="listing_description",
            credits_consumed=5,
            tokens_used=2000,
        )
        db_session.add(old_event)
        await db_session.flush()

        # Manually set created_at to last month (bypassing default)
        from sqlalchemy import update
        await db_session.execute(
            update(UsageEvent)
            .where(UsageEvent.id == old_event.id)
            .values(created_at=last_month)
        )
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/billing/usage", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Old event should not count
        assert data["credits_used"] == 0
        assert data["credits_remaining"] == 1000
