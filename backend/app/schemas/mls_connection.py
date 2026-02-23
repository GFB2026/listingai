from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer


class MLSConnectionCreate(BaseModel):
    provider: str  # trestle, bridge, spark
    name: str
    base_url: str
    client_id: str
    client_secret: str
    sync_enabled: bool = True


class MLSConnectionUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    sync_enabled: bool | None = None


class MLSConnectionResponse(BaseModel):
    id: str | UUID
    provider: str
    name: str | None
    base_url: str
    sync_enabled: bool
    last_sync_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v):
        return str(v) if v is not None else None


class MLSConnectionListResponse(BaseModel):
    connections: list[MLSConnectionResponse]


class MLSConnectionTestResult(BaseModel):
    success: bool
    message: str
    property_count: int | None = None


class MLSConnectionStatus(BaseModel):
    id: str
    name: str | None
    sync_enabled: bool
    last_sync_at: datetime | None
    sync_watermark: str | None
    listing_count: int
