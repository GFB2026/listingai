from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ListingResponse(BaseModel):
    id: str
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


class ListingListResponse(BaseModel):
    listings: list[ListingResponse]
    total: int
    page: int
    page_size: int


class ListingManualCreate(BaseModel):
    address_full: str
    address_street: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zip: str | None = None
    price: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: Decimal | None = None
    sqft: int | None = None
    lot_sqft: int | None = None
    year_built: int | None = None
    property_type: str | None = None
    status: str = "active"
    description_original: str | None = None
    features: list[str] | None = None
    photos: list[dict] | None = None


class ListingFilterParams(BaseModel):
    status: str | None = None
    property_type: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    city: str | None = None
    agent_id: str | None = None
    page: int = 1
    page_size: int = 20
