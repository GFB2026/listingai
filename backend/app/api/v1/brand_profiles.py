from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db
from app.models.brand_profile import BrandProfile
from app.models.user import User
from app.schemas.brand_profile import (
    BrandProfileCreate,
    BrandProfileResponse,
    BrandProfileUpdate,
)

router = APIRouter()


@router.get("", response_model=list[BrandProfileResponse])
async def list_brand_profiles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(BrandProfile)
        .where(BrandProfile.tenant_id == user.tenant_id)
        .order_by(BrandProfile.is_default.desc(), BrandProfile.name)
    )
    return result.scalars().all()


@router.post("", response_model=BrandProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_profile(
    request: BrandProfileCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    # If this is set as default, atomically unset other defaults
    if request.is_default:
        await db.execute(
            sa_update(BrandProfile)
            .where(
                BrandProfile.tenant_id == user.tenant_id,
                BrandProfile.is_default.is_(True),
            )
            .values(is_default=False)
        )

    profile = BrandProfile(
        tenant_id=user.tenant_id,
        name=request.name,
        is_default=request.is_default,
        voice_description=request.voice_description,
        vocabulary=request.vocabulary or [],
        avoid_words=request.avoid_words or [],
        sample_content=request.sample_content,
        settings=request.settings or {},
    )
    db.add(profile)
    await db.flush()
    return profile


@router.patch("/{profile_id}", response_model=BrandProfileResponse)
async def update_brand_profile(
    profile_id: str,
    update: BrandProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.id == UUID(profile_id),
            BrandProfile.tenant_id == user.tenant_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    update_data = update.model_dump(exclude_unset=True)

    # If setting this profile as default, atomically unset other defaults first
    if update_data.get("is_default") is True:
        await db.execute(
            sa_update(BrandProfile)
            .where(
                BrandProfile.tenant_id == user.tenant_id,
                BrandProfile.is_default.is_(True),
                BrandProfile.id != profile.id,
            )
            .values(is_default=False)
        )

    for field, value in update_data.items():
        setattr(profile, field, value)

    db.add(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand_profile(
    profile_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.id == UUID(profile_id),
            BrandProfile.tenant_id == user.tenant_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    await db.delete(profile)
