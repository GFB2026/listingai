from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class BrandProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_default: bool = False
    voice_description: str | None = Field(default=None, max_length=5000)
    vocabulary: list[str] | None = Field(default=None, max_length=200)
    avoid_words: list[str] | None = Field(default=None, max_length=200)
    sample_content: str | None = Field(default=None, max_length=10000)
    settings: dict | None = None


class BrandProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_default: bool | None = None
    voice_description: str | None = Field(default=None, max_length=5000)
    vocabulary: list[str] | None = Field(default=None, max_length=200)
    avoid_words: list[str] | None = Field(default=None, max_length=200)
    sample_content: str | None = Field(default=None, max_length=10000)
    settings: dict | None = None


class BrandProfileResponse(BaseModel):
    id: str | UUID
    name: str
    is_default: bool
    voice_description: str | None
    vocabulary: list | None
    avoid_words: list | None
    sample_content: str | None
    settings: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v):
        return str(v)
