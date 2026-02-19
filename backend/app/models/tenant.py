import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="free")
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255))
    monthly_generation_limit = Column(Integer, default=50)
    settings = Column(JSONB, default=dict)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="tenant", cascade="all, delete-orphan")
    brand_profiles = relationship("BrandProfile", back_populates="tenant", cascade="all, delete-orphan")
    mls_connections = relationship("MLSConnection", back_populates="tenant", cascade="all, delete-orphan")
    content = relationship("Content", back_populates="tenant", cascade="all, delete-orphan")
