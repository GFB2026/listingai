from datetime import datetime

from pydantic import BaseModel


class BrandProfileCreate(BaseModel):
    name: str
    is_default: bool = False
    voice_description: str | None = None
    vocabulary: list[str] | None = None
    avoid_words: list[str] | None = None
    sample_content: str | None = None
    settings: dict | None = None


class BrandProfileUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None
    voice_description: str | None = None
    vocabulary: list[str] | None = None
    avoid_words: list[str] | None = None
    sample_content: str | None = None
    settings: dict | None = None


class BrandProfileResponse(BaseModel):
    id: str
    name: str
    is_default: bool
    voice_description: str | None
    vocabulary: list | None
    avoid_words: list | None
    sample_content: str | None
    settings: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
