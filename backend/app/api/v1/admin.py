from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.content import Content
from app.models.listing import Listing
from app.models.user import User

router = APIRouter()


class AdminStatsResponse(BaseModel):
    total_users: int
    total_listings: int
    total_content: int


@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    users = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == user.tenant_id)
    )
    listings = await db.execute(
        select(func.count(Listing.id)).where(Listing.tenant_id == user.tenant_id)
    )
    content_count = await db.execute(
        select(func.count(Content.id)).where(Content.tenant_id == user.tenant_id)
    )

    return {
        "total_users": users.scalar(),
        "total_listings": listings.scalar(),
        "total_content": content_count.scalar(),
    }
