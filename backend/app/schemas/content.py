from datetime import datetime

from pydantic import BaseModel


class ContentGenerateRequest(BaseModel):
    listing_id: str
    content_type: str  # listing_description, social_instagram, social_facebook, etc.
    tone: str = "professional"  # luxury, professional, casual, friendly, urgent
    brand_profile_id: str | None = None
    instructions: str | None = None
    variants: int = 1


class ContentResponse(BaseModel):
    id: str
    content_type: str
    tone: str | None
    body: str
    metadata: dict
    status: str
    ai_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    generation_time_ms: int | None
    version: int
    listing_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentGenerateResponse(BaseModel):
    content: list[ContentResponse]
    usage: dict


class ContentUpdate(BaseModel):
    body: str | None = None
    status: str | None = None
    metadata: dict | None = None


class ContentListResponse(BaseModel):
    content: list[ContentResponse]
    total: int
    page: int
    page_size: int


class ContentBatchRequest(BaseModel):
    listing_ids: list[str]
    content_type: str
    tone: str = "professional"
    brand_profile_id: str | None = None
