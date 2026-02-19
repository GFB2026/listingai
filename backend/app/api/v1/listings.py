from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db
from app.models.listing import Listing
from app.models.user import User
from app.schemas.listing import (
    ListingListResponse,
    ListingManualCreate,
    ListingResponse,
)

router = APIRouter()


@router.get("", response_model=ListingListResponse)
async def list_listings(
    status_filter: str | None = Query(None, alias="status"),
    property_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    city: str | None = None,
    agent_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    query = select(Listing).where(Listing.tenant_id == user.tenant_id)

    if status_filter:
        query = query.where(Listing.status == status_filter)
    if property_type:
        query = query.where(Listing.property_type == property_type)
    if min_price is not None:
        query = query.where(Listing.price >= min_price)
    if max_price is not None:
        query = query.where(Listing.price <= max_price)
    if city:
        query = query.where(Listing.address_city.ilike(f"%{city}%"))
    if agent_id:
        query = query.where(Listing.listing_agent_id == UUID(agent_id))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.order_by(Listing.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    listings = result.scalars().all()

    return ListingListResponse(
        listings=[ListingResponse.model_validate(l) for l in listings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(Listing).where(
            Listing.id == UUID(listing_id),
            Listing.tenant_id == user.tenant_id,
        )
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(user: User = Depends(get_current_user)):
    from app.workers.tasks.mls_sync import sync_mls_listings

    sync_mls_listings.delay(str(user.tenant_id))
    return {"message": "MLS sync triggered", "status": "queued"}


@router.post("/manual", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_listing(
    request: ListingManualCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    listing = Listing(
        tenant_id=user.tenant_id,
        address_full=request.address_full,
        address_street=request.address_street,
        address_city=request.address_city,
        address_state=request.address_state,
        address_zip=request.address_zip,
        price=request.price,
        bedrooms=request.bedrooms,
        bathrooms=request.bathrooms,
        sqft=request.sqft,
        lot_sqft=request.lot_sqft,
        year_built=request.year_built,
        property_type=request.property_type,
        status=request.status,
        description_original=request.description_original,
        features=request.features or [],
        photos=request.photos or [],
        listing_agent_id=user.id,
    )
    db.add(listing)
    await db.flush()
    return listing
