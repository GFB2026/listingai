from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantResponse, TenantUpdate

router = APIRouter()


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/current", response_model=TenantResponse)
async def update_current_tenant(
    update: TenantUpdate,
    user: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if update.name is not None:
        tenant.name = update.name
    if update.settings is not None:
        tenant.settings = update.settings

    db.add(tenant)
    return tenant
