"""Tests for billing service."""
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent
from app.services.billing_service import BillingService


class TestGetCurrentUsage:
    @pytest.mark.asyncio
    async def test_no_usage(self, db_session: AsyncSession, test_tenant: Tenant):
        service = BillingService(db_session)
        result = await service.get_current_usage(test_tenant.id)

        assert result["credits_used"] == 0
        assert result["credits_limit"] == 1000
        assert result["credits_remaining"] == 1000
        assert result["tokens_used"] == 0
        assert result["total_events"] == 0
        assert result["plan"] == "professional"

    @pytest.mark.asyncio
    async def test_with_usage(
        self, db_session: AsyncSession, test_tenant: Tenant, test_user
    ):
        # Create some usage events
        event = UsageEvent(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            event_type="content_generation",
            content_type="listing_description",
            tokens_used=500,
            credits_consumed=3,
        )
        db_session.add(event)
        await db_session.flush()

        service = BillingService(db_session)
        result = await service.get_current_usage(test_tenant.id)

        assert result["credits_used"] == 3
        assert result["credits_remaining"] == 997  # 1000 - 3
        assert result["tokens_used"] == 500
        assert result["total_events"] == 1


class TestCreateOrUpdateSubscription:
    @pytest.mark.asyncio
    async def test_new_customer(self, db_session: AsyncSession, test_tenant: Tenant):
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"

        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test123"

        with (
            patch(
                "app.services.billing_service.stripe.Customer.create",
                return_value=mock_customer,
            ),
            patch(
                "app.services.billing_service"
                ".stripe.Subscription.create",
                return_value=mock_subscription,
            ),
            patch(
                "app.services.billing_service.get_settings",
            ) as mock_settings,
        ):
            mock_settings.return_value.stripe_secret_key = "sk_test"
            mock_settings.return_value.stripe_price_id_starter = "price_starter"
            mock_settings.return_value.stripe_price_id_professional = "price_pro"
            mock_settings.return_value.stripe_price_id_enterprise = "price_ent"

            service = BillingService(db_session)
            result = await service.create_or_update_subscription(
                test_tenant.id, "price_pro"
            )

        assert result["subscription_id"] == "sub_test123"
        assert result["plan"] == "professional"
        assert result["monthly_limit"] == 1000
        assert test_tenant.stripe_customer_id == "cus_test123"

    @pytest.mark.asyncio
    async def test_existing_customer(self, db_session: AsyncSession, test_tenant: Tenant):
        test_tenant.stripe_customer_id = "cus_existing"
        db_session.add(test_tenant)
        await db_session.flush()

        mock_subscription = MagicMock()
        mock_subscription.id = "sub_new"

        with (
            patch(
                "app.services.billing_service.stripe.Customer.create",
            ) as mock_create,
            patch(
                "app.services.billing_service"
                ".stripe.Subscription.create",
                return_value=mock_subscription,
            ),
            patch(
                "app.services.billing_service.get_settings",
            ) as mock_settings,
        ):
            mock_settings.return_value.stripe_secret_key = "sk_test"
            mock_settings.return_value.stripe_price_id_starter = "price_starter"
            mock_settings.return_value.stripe_price_id_professional = "price_pro"
            mock_settings.return_value.stripe_price_id_enterprise = "price_ent"

            service = BillingService(db_session)
            result = await service.create_or_update_subscription(
                test_tenant.id, "price_starter"
            )

        # Should NOT have created a new customer
        mock_create.assert_not_called()
        assert result["plan"] == "starter"
        assert result["monthly_limit"] == 200

    @pytest.mark.asyncio
    async def test_stripe_error(self, db_session: AsyncSession, test_tenant: Tenant):
        import stripe

        mock_error = stripe.error.StripeError("Something went wrong")

        with (
            patch("app.services.billing_service.stripe.Customer.create", side_effect=mock_error),
            patch("app.services.billing_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.stripe_secret_key = "sk_test"

            service = BillingService(db_session)
            with pytest.raises(ValueError, match="Payment provider error"):
                await service.create_or_update_subscription(
                    test_tenant.id, "price_test"
                )

    @pytest.mark.asyncio
    async def test_invalid_request_error(self, db_session: AsyncSession, test_tenant: Tenant):
        """InvalidRequestError on subscription create."""
        import stripe

        test_tenant.stripe_customer_id = "cus_existing"
        db_session.add(test_tenant)
        await db_session.flush()

        mock_error = stripe.error.InvalidRequestError("No such price", param="price")

        with (
            patch(
                "app.services.billing_service.stripe.Subscription.create",
                side_effect=mock_error,
            ),
            patch("app.services.billing_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.stripe_secret_key = "sk_test"

            service = BillingService(db_session)
            with pytest.raises(ValueError, match="Invalid subscription request"):
                await service.create_or_update_subscription(
                    test_tenant.id, "price_nonexistent"
                )

    @pytest.mark.asyncio
    async def test_stripe_error_on_subscription(
        self, db_session: AsyncSession, test_tenant: Tenant,
    ):
        """General StripeError on subscription create (not customer create)."""
        import stripe

        test_tenant.stripe_customer_id = "cus_existing"
        db_session.add(test_tenant)
        await db_session.flush()

        mock_error = stripe.error.StripeError("Payment failed")

        with (
            patch(
                "app.services.billing_service.stripe.Subscription.create",
                side_effect=mock_error,
            ),
            patch("app.services.billing_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.stripe_secret_key = "sk_test"

            service = BillingService(db_session)
            with pytest.raises(ValueError, match="Payment provider error"):
                await service.create_or_update_subscription(
                    test_tenant.id, "price_test"
                )

    @pytest.mark.asyncio
    async def test_plan_mapping_enterprise(self, db_session: AsyncSession, test_tenant: Tenant):
        test_tenant.stripe_customer_id = "cus_existing"
        db_session.add(test_tenant)
        await db_session.flush()

        mock_subscription = MagicMock()
        mock_subscription.id = "sub_ent"

        with (
            patch(
                "app.services.billing_service"
                ".stripe.Subscription.create",
                return_value=mock_subscription,
            ),
            patch(
                "app.services.billing_service.get_settings",
            ) as mock_settings,
        ):
            mock_settings.return_value.stripe_secret_key = "sk_test"
            mock_settings.return_value.stripe_price_id_starter = "price_starter"
            mock_settings.return_value.stripe_price_id_professional = "price_pro"
            mock_settings.return_value.stripe_price_id_enterprise = "price_ent"

            service = BillingService(db_session)
            result = await service.create_or_update_subscription(
                test_tenant.id, "price_ent"
            )

        assert result["plan"] == "enterprise"
        assert result["monthly_limit"] == 10000
