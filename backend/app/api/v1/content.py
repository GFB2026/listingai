import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db
from app.models.content import Content
from app.models.content_version import ContentVersion
from app.models.listing import Listing
from app.models.user import User
from app.schemas.content import (
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


@router.post("/generate", response_model=ContentGenerateResponse, status_code=status.HTTP_201_CREATED)
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

    # Generate content via AI service
    ai_service = AIService()
    content_service = ContentService(db)

    generated_items = []
    for _ in range(request.variants):
        start = time.time()
        result = await ai_service.generate(
            listing=listing,
            content_type=request.content_type,
            tone=request.tone,
            brand_profile_id=request.brand_profile_id,
            instructions=request.instructions,
            tenant_id=str(user.tenant_id),
            db=db,
        )
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
        generated_items.append(content_item)

    # Track usage
    await content_service.track_usage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        content_type=request.content_type,
        count=request.variants,
        tokens=sum(c.prompt_tokens + c.completion_tokens for c in generated_items if c.prompt_tokens),
    )

    return ContentGenerateResponse(
        content=[ContentResponse.model_validate(c) for c in generated_items],
        usage={
            "credits_consumed": request.variants,
            "credits_remaining": await content_service.get_remaining_credits(user.tenant_id),
        },
    )


@router.get("", response_model=ContentListResponse)
async def list_content(
    content_type: str | None = None,
    listing_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
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
            metadata=item.metadata or {},
            edited_by=user.id,
        )
        db.add(version)
        item.body = update.body
        item.version += 1

    if update.status is not None:
        item.status = update.status
    if update.metadata is not None:
        item.metadata = update.metadata

    db.add(item)
    return item


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

    export_service = ExportService()
    return await export_service.export(item, format)


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def batch_generate(
    request: ContentBatchRequest,
    user: User = Depends(get_current_user),
):
    from app.workers.tasks.content_batch import batch_generate_content

    batch_generate_content.delay(
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        listing_ids=request.listing_ids,
        content_type=request.content_type,
        tone=request.tone,
        brand_profile_id=request.brand_profile_id,
    )
    return {"message": "Batch generation queued", "listing_count": len(request.listing_ids)}
