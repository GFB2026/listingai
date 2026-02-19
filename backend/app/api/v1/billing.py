from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db, require_role
from app.models.user import User
from app.services.billing_service import BillingService

router = APIRouter()


@router.get("/usage")
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    billing = BillingService(db)
    return await billing.get_current_usage(user.tenant_id)


@router.post("/subscribe")
async def create_subscription(
    price_id: str,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    billing = BillingService(db)
    return await billing.create_or_update_subscription(user.tenant_id, price_id)
