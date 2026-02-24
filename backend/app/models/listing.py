import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class Listing(Base, TenantMixin, TimestampMixin):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mls_connection_id = Column(UUID(as_uuid=True), ForeignKey("mls_connections.id"))
    mls_listing_id = Column(String(50))
    # active, pending, sold, withdrawn, expired, coming_soon
    status = Column(String(20), server_default="active", nullable=False)
    property_type = Column(String(50))  # residential, condo, townhouse, land
    address_full = Column(String(500))
    address_street = Column(String(255))
    address_city = Column(String(100))
    address_state = Column(String(2))
    address_zip = Column(String(10))
    price = Column(Numeric(12, 2))
    bedrooms = Column(Integer)
    bathrooms = Column(Numeric(4, 1))
    sqft = Column(Integer)
    lot_sqft = Column(Integer)
    year_built = Column(Integer)
    description_original = Column(Text)
    features = Column(JSONB, default=list)
    photos = Column(JSONB, default=list)
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    list_date = Column(Date)
    listing_agent_name = Column(String(255))
    listing_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    raw_mls_data = Column(JSONB)
    last_synced_at = Column(DateTime(timezone=True))

    # Relationships
    tenant = relationship("Tenant", back_populates="listings")
    content = relationship("Content", back_populates="listing")
    mls_connection = relationship("MLSConnection", back_populates="listings")
