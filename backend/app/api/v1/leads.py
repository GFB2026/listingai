"""Authenticated lead management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db, require_role
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.user import User
from app.schemas.lead import (
    LeadActivityCreate,
    LeadActivityResponse,
    LeadAnalyticsSummary,
    LeadDetailResponse,
    LeadFunnelResponse,
    LeadFunnelStep,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from app.services.lead_service import LeadService

router = APIRouter()


def _lead_to_response(lead: Lead, agent_name: str | None = None) -> LeadResponse:
    resp = LeadResponse.model_validate(lead)
    resp.agent_name = agent_name
    return resp


@router.get("", response_model=LeadListResponse)
async def list_leads(
    pipeline_status: str | None = None,
    utm_source: str | None = None,
    agent_id: UUID | None = None,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List leads with filtering and pagination."""
    service = LeadService(db)
    leads, total = await service.list_leads(
        tenant_id=user.tenant_id,
        agent_id=agent_id,
        pipeline_status=pipeline_status,
        utm_source=utm_source,
        page=page,
        page_size=page_size,
        user_role=user.role,
        current_user_id=user.id,
    )

    # Batch-fetch agent names
    agent_ids = {lead.agent_id for lead in leads if lead.agent_id}
    agent_names = {}
    if agent_ids:
        result = await db.execute(
            select(User.id, User.full_name).where(User.id.in_(agent_ids))
        )
        agent_names = {row[0]: row[1] for row in result.all()}

    return LeadListResponse(
        leads=[
            _lead_to_response(lead, agent_names.get(lead.agent_id))
            for lead in leads
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/analytics/summary", response_model=LeadAnalyticsSummary)
async def analytics_summary(
    user: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Lead analytics summary: counts by status, source, agent."""
    service = LeadService(db)
    data = await service.get_summary(user.tenant_id)
    return LeadAnalyticsSummary(**data)


@router.get("/analytics/funnel", response_model=LeadFunnelResponse)
async def analytics_funnel(
    user: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Pipeline funnel conversion rates."""
    service = LeadService(db)
    funnel, total = await service.get_funnel(user.tenant_id)
    return LeadFunnelResponse(
        funnel=[LeadFunnelStep(**step) for step in funnel],
        total=total,
    )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get lead detail with activity timeline."""
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == user.tenant_id,
        )
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Agent can only see own leads
    if user.role == "agent" and lead.agent_id != user.id:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Fetch activities with user names
    result = await db.execute(
        select(LeadActivity)
        .where(LeadActivity.lead_id == lead.id)
        .order_by(LeadActivity.created_at.desc())
    )
    activities = result.scalars().all()

    # Get user names for activities
    activity_user_ids = {a.user_id for a in activities if a.user_id}
    user_names = {}
    if activity_user_ids:
        result = await db.execute(
            select(User.id, User.full_name).where(User.id.in_(activity_user_ids))
        )
        user_names = {row[0]: row[1] for row in result.all()}

    # Get agent name for lead
    agent_name = None
    if lead.agent_id:
        result = await db.execute(
            select(User.full_name).where(User.id == lead.agent_id)
        )
        agent_name = result.scalar_one_or_none()

    activity_responses = []
    for a in activities:
        resp = LeadActivityResponse.model_validate(a)
        resp.user_name = user_names.get(a.user_id)
        activity_responses.append(resp)

    return LeadDetailResponse(
        lead=_lead_to_response(lead, agent_name),
        activities=activity_responses,
    )


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    update: LeadUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update lead status, closed_value, or contact info."""
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == user.tenant_id,
        )
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if user.role == "agent" and lead.agent_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = LeadService(db)
    try:
        lead = await service.update_lead(
            lead,
            user,
            pipeline_status=update.pipeline_status,
            closed_value=update.closed_value,
            first_name=update.first_name,
            last_name=update.last_name,
            email=update.email,
            phone=update.phone,
            property_interest=update.property_interest,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _lead_to_response(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    user: User = Depends(require_role("admin", "broker")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Delete a lead (broker/admin only)."""
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == user.tenant_id,
        )
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.delete(lead)


@router.post("/{lead_id}/activities", response_model=LeadActivityResponse, status_code=201)
async def add_activity(
    lead_id: UUID,
    payload: LeadActivityCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Add a note or activity to a lead."""
    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == user.tenant_id,
        )
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if user.role == "agent" and lead.agent_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = LeadService(db)
    activity = await service.add_activity(
        lead,
        user,
        activity_type=payload.activity_type,
        note=payload.note,
    )

    resp = LeadActivityResponse.model_validate(activity)
    resp.user_name = user.full_name
    return resp
