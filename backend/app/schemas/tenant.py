from datetime import datetime

from pydantic import BaseModel


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    monthly_generation_limit: int
    settings: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    settings: dict | None = None
