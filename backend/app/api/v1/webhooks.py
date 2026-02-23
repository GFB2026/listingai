import redis.exceptions
import stripe
import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import get_settings
from app.core.redis import get_redis
from app.models.tenant import Tenant

router = APIRouter()
logger = structlog.get_logger()

# Map Stripe price IDs → (plan_name, monthly_generation_limit)
PLAN_MAP: dict[str, tuple[str, int]] = {}


def _get_plan_map() -> dict[str, tuple[str, int]]:
    """Lazy-load plan map from settings (not available at import time)."""
    if not PLAN_MAP:
        settings = get_settings()
        PLAN_MAP.update({
            settings.stripe_price_id_starter: ("starter", 200),
            settings.stripe_price_id_professional: ("professional", 1000),
            settings.stripe_price_id_enterprise: ("enterprise", 5000),
        })
    return PLAN_MAP


async def _update_tenant_plan(
    db: AsyncSession,
    stripe_customer_id: str,
    stripe_subscription_id: str | None,
    price_id: str | None,
) -> None:
    """Update a tenant's plan based on their Stripe subscription."""
    result = await db.execute(
        select(Tenant).where(Tenant.stripe_customer_id == stripe_customer_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        await logger.awarning("stripe_webhook_tenant_not_found", stripe_customer_id=stripe_customer_id)
        return

    if stripe_subscription_id is not None:
        tenant.stripe_subscription_id = stripe_subscription_id

    if price_id:
        plan_map = _get_plan_map()
        plan_info = plan_map.get(price_id)
        if plan_info:
            tenant.plan, tenant.monthly_generation_limit = plan_info
        else:
            await logger.awarning("stripe_unknown_price_id", price_id=price_id)
    else:
        # No price → downgrade to free
        tenant.plan = "free"
        tenant.monthly_generation_limit = 50

    db.add(tenant)
    await db.commit()
    await logger.ainfo(
        "tenant_plan_updated",
        tenant_id=str(tenant.id),
        plan=tenant.plan,
        limit=tenant.monthly_generation_limit,
    )


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    event_id = event["id"]
    data = event["data"]["object"]

    # Deduplicate: reject replayed events (idempotency window: 24 hours)
    try:
        r = await get_redis()
        dedup_key = f"stripe_event:{event_id}"
        if await r.exists(dedup_key):
            await logger.ainfo("stripe_webhook_duplicate", event_id=event_id)
            return {"status": "already_processed"}
        await r.setex(dedup_key, 86400, "1")  # 24-hour TTL
    except (redis.exceptions.RedisError, ConnectionError, OSError, RuntimeError):
        await logger.awarning("stripe_dedup_redis_unavailable", event_id=event_id)

    # Bind correlation ID for tracing webhook processing across logs
    structlog.contextvars.bind_contextvars(correlation_id=event_id)

    await logger.ainfo("stripe_webhook_received", event_type=event_type, event_id=event_id)

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        # Extract the first price ID from subscription items
        price_id = None
        items = data.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")

        await _update_tenant_plan(
            db=db,
            stripe_customer_id=data["customer"],
            stripe_subscription_id=data["id"],
            price_id=price_id,
        )

    elif event_type == "customer.subscription.deleted":
        await _update_tenant_plan(
            db=db,
            stripe_customer_id=data["customer"],
            stripe_subscription_id=None,
            price_id=None,  # triggers downgrade to free
        )

    elif event_type == "invoice.payment_failed":
        # Log the failure — the subscription will eventually be canceled by Stripe
        # if payment continues to fail, which triggers subscription.deleted above.
        customer_id = data.get("customer")
        result = await db.execute(
            select(Tenant).where(Tenant.stripe_customer_id == customer_id)
        )
        tenant = result.scalar_one_or_none()
        await logger.awarning(
            "stripe_payment_failed",
            stripe_customer_id=customer_id,
            tenant_id=str(tenant.id) if tenant else None,
            amount_due=data.get("amount_due"),
            attempt_count=data.get("attempt_count"),
        )

    return {"status": "ok"}
