"""Tests for Stripe webhook handlers."""
import json
from unittest.mock import AsyncMock, patch

import pytest
import stripe.error
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


class TestStripeWebhook:
    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "bad_sig"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_subscription_created_updates_plan(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        # Set the tenant's stripe customer ID
        test_tenant.stripe_customer_id = "cus_test123"
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_test",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "items": {
                        "data": [
                            {"price": {"id": "price_starter_test"}}
                        ]
                    },
                }
            },
        }

        # Mock Stripe signature verification and plan map
        with patch("stripe.Webhook.construct_event", return_value=event), \
             patch("app.api.v1.webhooks._get_plan_map", return_value={
                 "price_starter_test": ("starter", 200),
             }):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid_sig"},
            )

        assert response.status_code == 200
        # Verify tenant plan was updated
        await db_session.refresh(test_tenant)
        assert test_tenant.plan == "starter"
        assert test_tenant.monthly_generation_limit == 200
        assert test_tenant.stripe_subscription_id == "sub_test123"

    @pytest.mark.asyncio
    async def test_subscription_deleted_downgrades_to_free(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        test_tenant.stripe_customer_id = "cus_cancel123"
        test_tenant.plan = "professional"
        test_tenant.monthly_generation_limit = 1000
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_cancel",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_cancelled",
                    "customer": "cus_cancel123",
                }
            },
        }

        with patch("stripe.Webhook.construct_event", return_value=event):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid_sig"},
            )

        assert response.status_code == 200
        await db_session.refresh(test_tenant)
        assert test_tenant.plan == "free"
        assert test_tenant.monthly_generation_limit == 50

    @pytest.mark.asyncio
    async def test_unknown_customer_ignored(self, client: AsyncClient):
        event = {
            "id": "evt_unknown",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_unknown",
                    "customer": "cus_nonexistent",
                    "items": {"data": [{"price": {"id": "price_x"}}]},
                }
            },
        }

        with patch("stripe.Webhook.construct_event", return_value=event):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid_sig"},
            )

        # Should still return 200 (webhook processed, tenant not found is logged)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_payment_failed_logged(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        test_tenant.stripe_customer_id = "cus_fail123"
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_fail",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_fail123",
                    "amount_due": 4900,
                    "attempt_count": 2,
                }
            },
        }

        with patch("stripe.Webhook.construct_event", return_value=event):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid_sig"},
            )

        assert response.status_code == 200


class TestWebhookEdgeCases:
    @pytest.mark.asyncio
    async def test_invalid_payload_returns_400(self, client: AsyncClient):
        """ValueError from construct_event should return 400."""
        with patch(
            "stripe.Webhook.construct_event",
            side_effect=ValueError("bad payload"),
        ):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=b"bad",
                headers={"stripe-signature": "sig"},
            )
        assert response.status_code == 400
        assert "Invalid payload" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_signature_verification_error_returns_400(self, client: AsyncClient):
        """SignatureVerificationError should return 400."""
        with patch(
            "stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError("bad", "sig"),
        ):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=b"payload",
                headers={"stripe-signature": "bad"},
            )
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_duplicate_event_skipped(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        """Duplicate Stripe events should be deduplicated via Redis."""
        test_tenant.stripe_customer_id = "cus_dedup"
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_dedup_123",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_x",
                    "customer": "cus_dedup",
                    "items": {"data": [{"price": {"id": "price_x"}}]},
                }
            },
        }

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=True)  # already processed

        with (
            patch(
                "stripe.Webhook.construct_event",
                return_value=event,
            ),
            patch(
                "app.api.v1.webhooks.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
        ):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "already_processed"

    @pytest.mark.asyncio
    async def test_unknown_price_id_logged(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        """Unknown price_id should be logged but not crash."""
        test_tenant.stripe_customer_id = "cus_unknown_price"
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_unknown_price",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_y",
                    "customer": "cus_unknown_price",
                    "items": {"data": [{"price": {"id": "price_nonexistent"}}]},
                }
            },
        }

        with patch("stripe.Webhook.construct_event", return_value=event), \
             patch("app.api.v1.webhooks._get_plan_map", return_value={}):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_subscription_updated_changes_plan(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        """subscription.updated should upgrade/downgrade the tenant's plan."""
        test_tenant.stripe_customer_id = "cus_upgrade"
        test_tenant.plan = "starter"
        test_tenant.monthly_generation_limit = 200
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_upgrade",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_upgraded",
                    "customer": "cus_upgrade",
                    "items": {
                        "data": [
                            {"price": {"id": "price_professional_test"}}
                        ]
                    },
                }
            },
        }

        with patch("stripe.Webhook.construct_event", return_value=event), \
             patch("app.api.v1.webhooks._get_plan_map", return_value={
                 "price_professional_test": ("professional", 1000),
             }):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid"},
            )

        assert response.status_code == 200
        await db_session.refresh(test_tenant)
        assert test_tenant.plan == "professional"
        assert test_tenant.monthly_generation_limit == 1000
        assert test_tenant.stripe_subscription_id == "sub_upgraded"

    @pytest.mark.asyncio
    async def test_redis_unavailable_still_processes(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        """If Redis is down, webhook should still process (no dedup, but no crash)."""
        test_tenant.stripe_customer_id = "cus_redis_down"
        test_tenant.plan = "free"
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_redis_down",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_redis",
                    "customer": "cus_redis_down",
                    "items": {"data": [{"price": {"id": "price_starter_t"}}]},
                }
            },
        }

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

        with (
            patch(
                "stripe.Webhook.construct_event",
                return_value=event,
            ),
            patch(
                "app.api.v1.webhooks.get_redis",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch(
                "app.api.v1.webhooks._get_plan_map",
                return_value={
                    "price_starter_t": ("starter", 200),
                },
            ),
        ):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid"},
            )

        assert response.status_code == 200
        await db_session.refresh(test_tenant)
        assert test_tenant.plan == "starter"

    @pytest.mark.asyncio
    async def test_missing_signature_header(self, client: AsyncClient):
        """Missing stripe-signature header should return 400."""
        with patch(
            "stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError("no sig", ""),
        ):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=b"{}",
            )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unhandled_event_type_returns_ok(self, client: AsyncClient):
        """Unknown event types should be accepted but not processed."""
        event = {
            "id": "evt_unknown_type",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test"}},
        }

        with patch("stripe.Webhook.construct_event", return_value=event):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_subscription_with_empty_items(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant: Tenant
    ):
        """Subscription event with empty items list should downgrade to free."""
        test_tenant.stripe_customer_id = "cus_empty_items"
        test_tenant.plan = "professional"
        test_tenant.monthly_generation_limit = 1000
        db_session.add(test_tenant)
        await db_session.flush()

        event = {
            "id": "evt_empty_items",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_empty",
                    "customer": "cus_empty_items",
                    "items": {"data": []},
                }
            },
        }

        with patch("stripe.Webhook.construct_event", return_value=event):
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "valid"},
            )

        assert response.status_code == 200
        await db_session.refresh(test_tenant)
        assert test_tenant.plan == "free"
        assert test_tenant.monthly_generation_limit == 50
