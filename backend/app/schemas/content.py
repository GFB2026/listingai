from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator


class ContentType(StrEnum):
    LISTING_DESCRIPTION = "listing_description"
    SOCIAL_INSTAGRAM = "social_instagram"
    SOCIAL_FACEBOOK = "social_facebook"
    SOCIAL_LINKEDIN = "social_linkedin"
    SOCIAL_X = "social_x"
    EMAIL_JUST_LISTED = "email_just_listed"
    EMAIL_OPEN_HOUSE = "email_open_house"
    EMAIL_DRIP = "email_drip"
    FLYER = "flyer"
    VIDEO_SCRIPT = "video_script"
    # Event-specific content types
    OPEN_HOUSE_INVITE = "open_house_invite"
    PRICE_REDUCTION = "price_reduction"
    JUST_SOLD = "just_sold"


class Tone(StrEnum):
    LUXURY = "luxury"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    URGENT = "urgent"


class ContentGenerateRequest(BaseModel):
    listing_id: UUID
    content_type: ContentType
    tone: Tone = Tone.PROFESSIONAL
    brand_profile_id: UUID | None = None
    instructions: str | None = Field(default=None, max_length=2000)
    event_details: str | None = Field(default=None, max_length=2000)
    variants: int = Field(default=1, ge=1, le=5)


class ContentResponse(BaseModel):
    id: str | UUID
    content_type: str
    tone: str | None
    body: str
    metadata: dict = Field(validation_alias="content_metadata")
    status: str
    ai_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    generation_time_ms: int | None
    version: int
    listing_id: str | UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "listing_id")
    def serialize_uuids(self, v):
        return str(v) if v is not None else None


class ContentGenerateResponse(BaseModel):
    content: list[ContentResponse]
    usage: dict


class ContentUpdate(BaseModel):
    body: str | None = Field(default=None, max_length=50000)
    status: str | None = Field(default=None, pattern=r"^(draft|published|archived)$")
    metadata: dict | None = None


class ContentListResponse(BaseModel):
    content: list[ContentResponse]
    total: int
    page: int
    page_size: int


class ContentBatchRequest(BaseModel):
    listing_ids: list[str] = Field(..., min_length=1, max_length=50)
    content_type: ContentType
    tone: Tone = Tone.PROFESSIONAL
    brand_profile_id: str | None = None

    @field_validator("listing_ids")
    @classmethod
    def validate_and_deduplicate_listing_ids(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for lid in v:
            # Validate UUID format
            try:
                UUID(lid)
            except ValueError as e:
                raise ValueError(f"Invalid UUID: {lid}") from e
            if lid not in seen:
                seen.add(lid)
                unique.append(lid)
        return unique

    @field_validator("brand_profile_id")
    @classmethod
    def validate_brand_profile_uuid(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                UUID(v)
            except ValueError as e:
                raise ValueError(f"Invalid UUID: {v}") from e
        return v


class BatchQueueResponse(BaseModel):
    message: str
    listing_count: int


class SyncQueueResponse(BaseModel):
    message: str
    status: str
