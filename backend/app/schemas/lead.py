from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_serializer


# ── Public lead submission ──────────────────────────────────────

class LeadCreate(BaseModel):
    """Public lead form submission."""
    tenant_slug: str = Field(..., max_length=100)
    agent_slug: str = Field(..., max_length=100)
    listing_id: str | None = None
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    message: str | None = Field(default=None, max_length=5000)
    property_interest: str | None = Field(default=None, max_length=500)
    # UTM
    utm_source: str | None = Field(default=None, max_length=200)
    utm_medium: str | None = Field(default=None, max_length=200)
    utm_campaign: str | None = Field(default=None, max_length=200)
    utm_content: str | None = Field(default=None, max_length=200)
    utm_term: str | None = Field(default=None, max_length=200)
    # Attribution
    session_id: str | None = Field(default=None, max_length=100)
    referrer_url: str | None = Field(default=None, max_length=2000)
    landing_url: str | None = Field(default=None, max_length=2000)


class PageVisitCreate(BaseModel):
    """Public page visit tracking."""
    tenant_slug: str = Field(..., max_length=100)
    agent_slug: str = Field(..., max_length=100)
    listing_id: str | None = None
    session_id: str | None = Field(default=None, max_length=100)
    utm_source: str | None = Field(default=None, max_length=200)
    utm_medium: str | None = Field(default=None, max_length=200)
    utm_campaign: str | None = Field(default=None, max_length=200)
    utm_content: str | None = Field(default=None, max_length=200)
    utm_term: str | None = Field(default=None, max_length=200)
    referrer_url: str | None = Field(default=None, max_length=2000)
    landing_url: str | None = Field(default=None, max_length=2000)


# ── Authenticated lead management ──────────────────────────────

class LeadUpdate(BaseModel):
    pipeline_status: str | None = Field(default=None, max_length=20)
    closed_value: Decimal | None = Field(default=None, ge=0, le=1_000_000_000)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    property_interest: str | None = Field(default=None, max_length=500)


class LeadActivityCreate(BaseModel):
    activity_type: str = Field(..., max_length=30)
    note: str | None = Field(default=None, max_length=5000)


class LeadResponse(BaseModel):
    id: str | UUID
    tenant_id: str | UUID
    agent_page_id: str | UUID | None
    agent_id: str | UUID | None
    listing_id: str | UUID | None
    first_name: str
    last_name: str | None
    email: str | None
    phone: str | None
    message: str | None
    property_interest: str | None
    pipeline_status: str
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    utm_term: str | None
    referrer_url: str | None
    landing_url: str | None
    closed_value: Decimal | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    agent_name: str | None = None

    model_config = {"from_attributes": True}

    @field_serializer("id", "tenant_id", "agent_page_id", "agent_id", "listing_id")
    def serialize_uuid(self, v):
        if v is None:
            return None
        return str(v)


class LeadListResponse(BaseModel):
    leads: list[LeadResponse]
    total: int
    page: int
    page_size: int


class LeadActivityResponse(BaseModel):
    id: str | UUID
    lead_id: str | UUID
    user_id: str | UUID | None
    activity_type: str
    old_value: str | None
    new_value: str | None
    note: str | None
    created_at: datetime
    user_name: str | None = None

    model_config = {"from_attributes": True}

    @field_serializer("id", "lead_id", "user_id")
    def serialize_uuid(self, v):
        if v is None:
            return None
        return str(v)


class LeadDetailResponse(BaseModel):
    lead: LeadResponse
    activities: list[LeadActivityResponse]


# ── Analytics ──────────────────────────────────────────────────

class LeadAnalyticsSummary(BaseModel):
    total_leads: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    by_agent: list[dict]
    total_closed_value: Decimal | None


class LeadFunnelStep(BaseModel):
    status: str
    count: int
    percentage: float


class LeadFunnelResponse(BaseModel):
    funnel: list[LeadFunnelStep]
    total: int
