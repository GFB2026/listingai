from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.content import Content
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent
from app.models.user import User

router = APIRouter()


@router.get("/stats")
async def admin_stats(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    tenants = await db.execute(select(func.count(Tenant.id)))
    users = await db.execute(select(func.count(User.id)))
    listings = await db.execute(select(func.count(Listing.id)))
    content_count = await db.execute(select(func.count(Content.id)))

    return {
        "total_tenants": tenants.scalar(),
        "total_users": users.scalar(),
        "total_listings": listings.scalar(),
        "total_content": content_count.scalar(),
    }
