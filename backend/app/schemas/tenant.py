from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class TenantResponse(BaseModel):
    id: str | UUID
    name: str
    slug: str
    plan: str
    monthly_generation_limit: int
    settings: dict
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v):
        return str(v) if v is not None else None


class TenantUpdate(BaseModel):
    name: str | None = None
    settings: dict | None = None
