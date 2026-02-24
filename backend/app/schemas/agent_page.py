from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class AgentPageCreate(BaseModel):
    user_id: str
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    photo_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    email_display: str | None = Field(default=None, max_length=255)
    theme: dict | None = None


class AgentPageUpdate(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    photo_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    email_display: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    theme: dict | None = None


class AgentPageResponse(BaseModel):
    id: str | UUID
    tenant_id: str | UUID
    user_id: str | UUID
    slug: str
    headline: str | None
    bio: str | None
    photo_url: str | None
    phone: str | None
    email_display: str | None
    is_active: bool
    theme: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "tenant_id", "user_id")
    def serialize_uuid(self, v):
        return str(v)


class AgentPageListResponse(BaseModel):
    agent_pages: list[AgentPageResponse]
    total: int


# Public-facing response (no tenant_id, user_id)
class AgentPagePublicResponse(BaseModel):
    slug: str
    headline: str | None
    bio: str | None
    photo_url: str | None
    phone: str | None
    email_display: str | None
    theme: dict | None
    agent_name: str | None = None

    model_config = {"from_attributes": True}
