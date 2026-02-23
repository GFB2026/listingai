"""Tests for Stripe webhook handlers."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
