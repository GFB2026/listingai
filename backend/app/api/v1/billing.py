from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db, require_role
from app.models.user import User
from app.services.billing_service import BillingService

router = APIRouter()


class UsageResponse(BaseModel):
    plan: str
    credits_used: int
    credits_limit: int
    credits_remaining: int
    tokens_used: int = 0
    total_events: int = 0

    model_config = {"from_attributes": True}


class SubscriptionResponse(BaseModel):
    subscription_id: str | None = None
    status: str
    url: str | None = None

    model_config = {"from_attributes": True}


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    billing = BillingService(db)
    return await billing.get_current_usage(user.tenant_id)


@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_subscription(
    price_id: str,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    billing = BillingService(db)
    try:
        return await billing.create_or_update_subscription(user.tenant_id, price_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
