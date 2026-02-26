import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db
from app.models.brand_profile import BrandProfile
from app.models.content import Content
from app.models.content_version import ContentVersion
from app.models.listing import Listing
from app.models.user import User
from app.schemas.content import (
    BatchQueueResponse,
    ContentBatchRequest,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ContentListResponse,
    ContentResponse,
    ContentUpdate,
)
from app.services.ai_service import AIService
from app.services.content_service import ContentService

router = APIRouter()


@router.post(
    "/generate", response_model=ContentGenerateResponse, status_code=status.HTTP_201_CREATED
)
async def generate_content(
    request: ContentGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Fetch listing
    result = await db.execute(
        select(Listing).where(
            Listing.id == UUID(request.listing_id),
            Listing.tenant_id == user.tenant_id,
        )
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Validate brand profile exists and belongs to tenant
    if request.brand_profile_id:
        bp_result = await db.execute(
            select(BrandProfile).where(
                BrandProfile.id == UUID(request.brand_profile_id),
                BrandProfile.tenant_id == user.tenant_id,
            )
        )
        if not bp_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Brand profile not found")

    # Check credit budget BEFORE calling Claude API
    content_service = ContentService(db)
    remaining = await content_service.get_remaining_credits(user.tenant_id)
    if remaining < request.variants:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. {remaining} remaining, {request.variants} required.",
        )

    # Generate content via AI service
    ai_service = AIService()

    generated_items = []
    for _i in range(request.variants):
        # Re-check credits before each variant to prevent over-consumption
        remaining = await content_service.get_remaining_credits(user.tenant_id)
        if remaining < 1:
            if not generated_items:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient credits. 0 remaining.",
                )
            break

        start = time.time()
        try:
            result = await ai_service.generate(
                listing=listing,
                content_type=request.content_type,
                tone=request.tone,
                brand_profile_id=request.brand_profile_id,
                instructions=request.instructions,
                event_details=request.event_details or "",
                tenant_id=str(user.tenant_id),
                db=db,
            )
        except Exception:
            if not generated_items:
                raise
            break

        generation_time_ms = int((time.time() - start) * 1000)

        content_item = await content_service.create(
            tenant_id=user.tenant_id,
            listing_id=listing.id,
            user_id=user.id,
            content_type=request.content_type,
            tone=request.tone,
            brand_profile_id=UUID(request.brand_profile_id) if request.brand_profile_id else None,
            body=result["body"],
            metadata=result.get("metadata", {}),
            ai_model=result["model"],
            prompt_tokens=result.get("prompt_tokens", 0),
            completion_tokens=result.get("completion_tokens", 0),
            generation_time_ms=generation_time_ms,
        )

        # Track usage immediately per-variant so credits are consumed atomically
        await content_service.track_usage(
            tenant_id=user.tenant_id,
            user_id=user.id,
            content_type=request.content_type,
            count=1,
            tokens=(result.get("prompt_tokens", 0) + result.get("completion_tokens", 0)),
        )
        generated_items.append(content_item)

    return ContentGenerateResponse(
        content=[ContentResponse.model_validate(c) for c in generated_items],
        usage={
            "credits_consumed": len(generated_items),
            "credits_remaining": await content_service.get_remaining_credits(user.tenant_id),
        },
    )


@router.get("", response_model=ContentListResponse)
async def list_content(
    content_type: str | None = None,
    listing_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1, le=1000),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    query = select(Content).where(Content.tenant_id == user.tenant_id)

    if content_type:
        query = query.where(Content.content_type == content_type)
    if listing_id:
        query = query.where(Content.listing_id == UUID(listing_id))
    if status_filter:
        query = query.where(Content.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Content.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return ContentListResponse(
        content=[ContentResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(Content).where(
            Content.id == UUID(content_id),
            Content.tenant_id == user.tenant_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


@router.patch("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: str,
    update: ContentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(Content).where(
            Content.id == UUID(content_id),
            Content.tenant_id == user.tenant_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    # Save version before editing body
    if update.body is not None and update.body != item.body:
        version = ContentVersion(
            content_id=item.id,
            version=item.version,
            body=item.body,
            content_metadata=item.content_metadata or {},
            edited_by=user.id,
        )
        db.add(version)
        item.body = update.body
        item.version += 1

    if update.status is not None:
        item.status = update.status
    if update.metadata is not None:
        item.content_metadata = update.metadata

    db.add(item)
    return item


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(Content).where(
            Content.id == UUID(content_id),
            Content.tenant_id == user.tenant_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    await db.delete(item)


@router.post("/{content_id}/regenerate", response_model=ContentResponse)
async def regenerate_content(
    content_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(Content).where(
            Content.id == UUID(content_id),
            Content.tenant_id == user.tenant_id,
        )
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Content not found")

    # Re-generate using same parameters
    request = ContentGenerateRequest(
        listing_id=str(original.listing_id),
        content_type=original.content_type,
        tone=original.tone or "professional",
        brand_profile_id=str(original.brand_profile_id) if original.brand_profile_id else None,
        variants=1,
    )
    response = await generate_content(request, user, db)
    return response.content[0]


@router.get("/{content_id}/export/{format}")
async def export_content(
    content_id: str,
    format: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    from app.models.tenant import Tenant
    from app.services.export_service import ExportService

    result = await db.execute(
        select(Content).where(
            Content.id == UUID(content_id),
            Content.tenant_id == user.tenant_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    # Flyer formats need the listing and branding config
    listing = None
    branding_settings = None
    if format in ("pptx", "flyer_pdf"):
        if item.listing_id:
            listing_result = await db.execute(
                select(Listing).where(Listing.id == item.listing_id)
            )
            listing = listing_result.scalar_one_or_none()

        # Try brand profile first, fall back to tenant settings
        if item.brand_profile_id:
            bp_result = await db.execute(
                select(BrandProfile).where(BrandProfile.id == item.brand_profile_id)
            )
            bp = bp_result.scalar_one_or_none()
            if bp and bp.settings:
                branding_settings = bp.settings
        if not branding_settings:
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.id == user.tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant and tenant.settings:
                branding_settings = tenant.settings

    export_service = ExportService()
    try:
        return await export_service.export(
            item, format, listing=listing, branding_settings=branding_settings
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batch", response_model=BatchQueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_generate(
    request: ContentBatchRequest,
    user: User = Depends(get_current_user),
):
    import structlog.contextvars

    from app.workers.tasks.content_batch import batch_generate_content

    ctx = structlog.contextvars.get_contextvars()
    correlation_id = ctx.get("request_id")

    batch_generate_content.delay(
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        listing_ids=request.listing_ids,
        content_type=request.content_type,
        tone=request.tone,
        brand_profile_id=request.brand_profile_id,
        correlation_id=correlation_id,
    )
    return BatchQueueResponse(
        message="Batch generation queued", listing_count=len(request.listing_ids)
    )
