from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db
from app.models.email_campaign import EmailCampaign
from app.models.tenant import Tenant
from app.models.user import User
from app.services.email_service import EmailService

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────


class EmailSendRequest(BaseModel):
    to_emails: list[EmailStr] = Field(..., min_length=1, max_length=1000)
    subject: str = Field(..., min_length=1, max_length=500)
    html_content: str = Field(..., min_length=1, max_length=200000)
    campaign_type: str = Field(default="manual", max_length=50)
    reply_to: EmailStr | None = None
    content_id: UUID | None = None
    listing_id: UUID | None = None


class EmailSendResponse(BaseModel):
    sent: int
    failed: int
    errors: list[str]
    campaign_id: str | None = None


class CampaignResponse(BaseModel):
    id: str
    subject: str
    from_email: str
    from_name: str | None
    recipient_count: int
    sent: int
    failed: int
    campaign_type: str
    created_at: str

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignResponse]
    total: int
    page: int
    page_size: int


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/send", response_model=EmailSendResponse, status_code=status.HTTP_201_CREATED)
async def send_email(
    request: EmailSendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Send an email campaign and track it."""
    service = EmailService()
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SendGrid API key not configured.",
        )

    # Get tenant for CAN-SPAM physical address
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    physical_address = None
    unsubscribe_url = None
    if tenant:
        settings = tenant.settings or {}
        physical_address = settings.get("physical_address")
        unsubscribe_url = settings.get("unsubscribe_url")

    campaign = await service.send_and_track(
        db=db,
        tenant_id=user.tenant_id,
        to_emails=request.to_emails,
        subject=request.subject,
        html_content=request.html_content,
        campaign_type=request.campaign_type,
        reply_to=request.reply_to,
        content_id=request.content_id,
        listing_id=request.listing_id,
        user_id=user.id,
        physical_address=physical_address,
        unsubscribe_url=unsubscribe_url,
    )

    return EmailSendResponse(
        sent=campaign.sent,
        failed=campaign.failed,
        errors=campaign.errors or [],
        campaign_id=str(campaign.id),
    )


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    campaign_type: str | None = None,
    page: int = Query(1, ge=1, le=1000),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List email campaigns for the current tenant."""
    query = select(EmailCampaign).where(EmailCampaign.tenant_id == user.tenant_id)

    if campaign_type:
        query = query.where(EmailCampaign.campaign_type == campaign_type)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(EmailCampaign.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return CampaignListResponse(
        campaigns=[
            CampaignResponse(
                id=str(c.id),
                subject=c.subject or "",
                from_email=c.from_email or "",
                from_name=c.from_name,
                recipient_count=c.recipient_count or 0,
                sent=c.sent or 0,
                failed=c.failed or 0,
                campaign_type=c.campaign_type or "",
                created_at=c.created_at.isoformat() if c.created_at else "",
            )
            for c in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/status")
async def email_status(
    user: User = Depends(get_current_user),
):
    """Check if email sending is configured."""
    service = EmailService()
    return {"configured": service.is_configured}
