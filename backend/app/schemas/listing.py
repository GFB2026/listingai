from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class ListingResponse(BaseModel):
    id: str | UUID
    mls_listing_id: str | None
    status: str | None
    property_type: str | None
    address_full: str | None
    address_city: str | None
    address_state: str | None
    address_zip: str | None
    price: Decimal | None
    bedrooms: int | None
    bathrooms: Decimal | None
    sqft: int | None
    year_built: int | None
    description_original: str | None
    features: list | None
    photos: list | None
    list_date: date | None
    listing_agent_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v):
        return str(v)


class ListingListResponse(BaseModel):
    listings: list[ListingResponse]
    total: int
    page: int
    page_size: int


class ListingManualCreate(BaseModel):
    address_full: str = Field(..., max_length=500)
    address_street: str | None = Field(default=None, max_length=200)
    address_city: str | None = Field(default=None, max_length=100)
    address_state: str | None = Field(default=None, max_length=50)
    address_zip: str | None = Field(default=None, max_length=20)
    price: Decimal | None = Field(default=None, ge=0, le=1_000_000_000)
    bedrooms: int | None = Field(default=None, ge=0, le=100)
    bathrooms: Decimal | None = Field(default=None, ge=0, le=100)
    sqft: int | None = Field(default=None, ge=0, le=1_000_000)
    lot_sqft: int | None = Field(default=None, ge=0, le=100_000_000)
    year_built: int | None = Field(default=None, ge=1600, le=2100)
    property_type: str | None = Field(default=None, max_length=50)
    status: str = Field(default="active", max_length=20)
    description_original: str | None = Field(default=None, max_length=10000)
    features: list[str] | None = Field(default=None, max_length=100)
    photos: list[dict] | None = Field(default=None, max_length=200)


class ListingFilterParams(BaseModel):
    status: str | None = Field(default=None, max_length=20)
    property_type: str | None = Field(default=None, max_length=50)
    min_price: Decimal | None = Field(default=None, ge=0, le=1_000_000_000)
    max_price: Decimal | None = Field(default=None, ge=0, le=1_000_000_000)
    city: str | None = Field(default=None, max_length=100)
    agent_id: str | None = None
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=20, ge=1, le=100)
