from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.social_service import SocialService

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────


class SocialPostRequest(BaseModel):
    listing_id: UUID | None = None
    content_id: UUID | None = None
    fb_text: str | None = Field(default=None, max_length=5000)
    ig_text: str | None = Field(default=None, max_length=2200)
    photo_url: str | None = Field(default=None, max_length=2000)
    listing_link: str | None = Field(default=None, max_length=2000)


class SocialPostResult(BaseModel):
    platform: str
    success: bool
    post_id: str | None = None
    error: str | None = None
    warning: str | None = None


class SocialPostResponse(BaseModel):
    results: list[SocialPostResult]


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/post", response_model=SocialPostResponse, status_code=status.HTTP_201_CREATED)
async def publish_social_post(
    request: SocialPostRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Publish content to configured social media platforms (Facebook + Instagram)."""
    # Load tenant settings for social credentials
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    service = SocialService.from_tenant_settings(tenant.settings or {})
    if not service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Social media credentials not configured."
                " Set page_access_token and facebook_page_id"
                " in tenant settings."
            ),
        )

    if not request.fb_text and not request.ig_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of fb_text or ig_text is required.",
        )

    posts = await service.post_and_track(
        db=db,
        tenant_id=user.tenant_id,
        fb_text=request.fb_text,
        ig_text=request.ig_text,
        photo_url=request.photo_url,
        listing_link=request.listing_link,
        content_id=request.content_id,
        listing_id=request.listing_id,
        user_id=user.id,
    )

    return SocialPostResponse(
        results=[
            SocialPostResult(
                platform=p.platform,
                success=p.status == "success",
                post_id=p.platform_post_id,
                error=p.error,
            )
            for p in posts
        ]
    )


@router.get("/status")
async def social_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Check if social media is configured for the current tenant."""
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    service = SocialService.from_tenant_settings(tenant.settings or {})
    return {
        "configured": service is not None,
        "facebook": service is not None,
        "instagram": service.has_instagram if service else False,
    }
