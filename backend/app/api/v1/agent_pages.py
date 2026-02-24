"""Agent page management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db, require_role
from app.models.agent_page import AgentPage
from app.models.user import User
from app.schemas.agent_page import (
    AgentPageCreate,
    AgentPageListResponse,
    AgentPageResponse,
    AgentPageUpdate,
)

router = APIRouter()


@router.get("", response_model=AgentPageListResponse)
async def list_agent_pages(
    user: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all agent pages."""
    result = await db.execute(
        select(AgentPage)
        .where(AgentPage.tenant_id == user.tenant_id)
        .order_by(AgentPage.created_at)
    )
    pages = result.scalars().all()
    return AgentPageListResponse(
        agent_pages=[AgentPageResponse.model_validate(p) for p in pages],
        total=len(pages),
    )


@router.post("", response_model=AgentPageResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_page(
    payload: AgentPageCreate,
    user: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new agent page."""
    # Check slug uniqueness
    existing = await db.execute(
        select(AgentPage).where(
            AgentPage.tenant_id == user.tenant_id,
            AgentPage.slug == payload.slug,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already in use")

    # Check user exists in tenant
    target_user_id = UUID(payload.user_id)
    user_result = await db.execute(
        select(User).where(
            User.id == target_user_id,
            User.tenant_id == user.tenant_id,
        )
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User not found in tenant")

    # Check user doesn't already have a page
    existing_page = await db.execute(
        select(AgentPage).where(
            AgentPage.tenant_id == user.tenant_id,
            AgentPage.user_id == target_user_id,
        )
    )
    if existing_page.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has an agent page")

    page = AgentPage(
        tenant_id=user.tenant_id,
        user_id=target_user_id,
        slug=payload.slug,
        headline=payload.headline,
        bio=payload.bio,
        photo_url=payload.photo_url,
        phone=payload.phone,
        email_display=payload.email_display,
        theme=payload.theme or {},
    )
    db.add(page)
    await db.flush()
    return page


@router.patch("/{page_id}", response_model=AgentPageResponse)
async def update_agent_page(
    page_id: str,
    update: AgentPageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update an agent page. Broker/admin can update any; agents can update their own."""
    result = await db.execute(
        select(AgentPage).where(
            AgentPage.id == UUID(page_id),
            AgentPage.tenant_id == user.tenant_id,
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Agent page not found")

    # Agents can only update their own page
    if user.role == "agent" and page.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if update.slug is not None and update.slug != page.slug:
        # Check slug uniqueness
        existing = await db.execute(
            select(AgentPage).where(
                AgentPage.tenant_id == user.tenant_id,
                AgentPage.slug == update.slug,
                AgentPage.id != page.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already in use")
        page.slug = update.slug

    if update.headline is not None:
        page.headline = update.headline
    if update.bio is not None:
        page.bio = update.bio
    if update.photo_url is not None:
        page.photo_url = update.photo_url
    if update.phone is not None:
        page.phone = update.phone
    if update.email_display is not None:
        page.email_display = update.email_display
    if update.is_active is not None:
        page.is_active = update.is_active
    if update.theme is not None:
        page.theme = update.theme

    db.add(page)
    return page


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_page(
    page_id: str,
    user: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Deactivate an agent page (soft delete)."""
    result = await db.execute(
        select(AgentPage).where(
            AgentPage.id == UUID(page_id),
            AgentPage.tenant_id == user.tenant_id,
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Agent page not found")

    page.is_active = False
    db.add(page)
