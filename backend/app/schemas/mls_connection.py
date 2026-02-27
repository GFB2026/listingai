from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_serializer, field_validator

VALID_PROVIDERS = ("trestle", "bridge")

# Default base URLs per provider so the frontend can pre-fill them
PROVIDER_DEFAULT_URLS: dict[str, str] = {
    "trestle": "https://api-trestle.corelogic.com",
    "bridge": "https://api.bridgedataoutput.com",
}


class MLSConnectionCreate(BaseModel):
    provider: str  # trestle, bridge
    name: str
    base_url: str
    client_id: str
    client_secret: str
    sync_enabled: bool = True
    settings: dict | None = None  # Provider-specific: {"dataset": "beachesmls"} for Bridge

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_PROVIDERS:
            raise ValueError(f"provider must be one of {VALID_PROVIDERS}, got '{v}'")
        return v

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, v: dict | None, info) -> dict | None:
        """Validate provider-specific settings.

        Bridge connections require a 'dataset' key (e.g., 'beachesmls').
        """
        if v is None:
            return v
        # Only allow known keys to prevent junk data
        allowed_keys = {"dataset"}
        unknown = set(v.keys()) - allowed_keys
        if unknown:
            raise ValueError(f"Unknown settings keys: {unknown}. Allowed: {allowed_keys}")
        return v


class MLSConnectionUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    sync_enabled: bool | None = None
    settings: dict | None = None  # Provider-specific settings

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        allowed_keys = {"dataset"}
        unknown = set(v.keys()) - allowed_keys
        if unknown:
            raise ValueError(f"Unknown settings keys: {unknown}. Allowed: {allowed_keys}")
        return v


class MLSConnectionResponse(BaseModel):
    id: str | UUID
    provider: str
    name: str | None
    base_url: str
    sync_enabled: bool
    last_sync_at: datetime | None
    created_at: datetime
    settings: dict | None = None

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
    provider: str
    sync_enabled: bool
    last_sync_at: datetime | None
    sync_watermark: str | None
    listing_count: int
