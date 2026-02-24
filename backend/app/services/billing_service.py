from datetime import UTC, datetime
from uuid import UUID

import stripe
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent

logger = structlog.get_logger()


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        settings = get_settings()
        stripe.api_key = settings.stripe_secret_key

    async def get_current_usage(self, tenant_id: UUID) -> dict:
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get usage counts
        result = await self.db.execute(
            select(
                func.count(UsageEvent.id).label("total_events"),
                func.coalesce(func.sum(UsageEvent.credits_consumed), 0).label("credits_used"),
                func.coalesce(func.sum(UsageEvent.tokens_used), 0).label("tokens_used"),
            ).where(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.created_at >= month_start,
            )
        )
        row = result.one()

        # Get tenant limit
        tenant_result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = tenant_result.scalar_one()

        return {
            "period_start": month_start.isoformat(),
            "period_end": now.isoformat(),
            "credits_used": row.credits_used,
            "credits_limit": tenant.monthly_generation_limit,
            "credits_remaining": max(0, tenant.monthly_generation_limit - row.credits_used),
            "tokens_used": row.tokens_used,
            "total_events": row.total_events,
            "plan": tenant.plan,
        }

    async def create_or_update_subscription(self, tenant_id: UUID, price_id: str) -> dict:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()

        # Create Stripe customer if needed
        if not tenant.stripe_customer_id:
            try:
                customer = stripe.Customer.create(
                    metadata={"tenant_id": str(tenant_id), "tenant_name": tenant.name},
                )
            except stripe.error.StripeError as exc:
                await logger.aerror(
                    "stripe_customer_create_failed",
                    tenant_id=str(tenant_id), error=str(exc),
                )
                raise ValueError(
                    f"Payment provider error: "
                    f"{exc.user_message or 'please try again later'}"
                ) from exc
            tenant.stripe_customer_id = customer.id
            self.db.add(tenant)
            await self.db.flush()

        # Create subscription
        try:
            subscription = stripe.Subscription.create(
                customer=tenant.stripe_customer_id,
                items=[{"price": price_id}],
            )
        except stripe.error.InvalidRequestError as exc:
            await logger.aerror(
                "stripe_invalid_request",
                tenant_id=str(tenant_id), error=str(exc),
            )
            raise ValueError(
                f"Invalid subscription request: "
                f"{exc.user_message or str(exc)}"
            ) from exc
        except stripe.error.StripeError as exc:
            await logger.aerror(
                "stripe_subscription_create_failed",
                tenant_id=str(tenant_id), error=str(exc),
            )
            raise ValueError(
                f"Payment provider error: "
                f"{exc.user_message or 'please try again later'}"
            ) from exc

        # Update tenant
        tenant.stripe_subscription_id = subscription.id

        # Set plan based on price
        settings = get_settings()
        if price_id == settings.stripe_price_id_starter:
            tenant.plan = "starter"
            tenant.monthly_generation_limit = 200
        elif price_id == settings.stripe_price_id_professional:
            tenant.plan = "professional"
            tenant.monthly_generation_limit = 1000
        elif price_id == settings.stripe_price_id_enterprise:
            tenant.plan = "enterprise"
            tenant.monthly_generation_limit = 10000

        self.db.add(tenant)

        return {
            "subscription_id": subscription.id,
            "plan": tenant.plan,
            "monthly_limit": tenant.monthly_generation_limit,
        }
