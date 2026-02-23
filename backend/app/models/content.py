import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class Content(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    brand_profile_id = Column(UUID(as_uuid=True), ForeignKey("brand_profiles.id"))
    content_type = Column(String(30), nullable=False)
    tone = Column(String(30))
    body = Column(Text, nullable=False)
    content_metadata = Column("metadata", JSONB, default=dict)
    status = Column(String(20), server_default="draft", nullable=False)  # draft, approved, published, archived
    ai_model = Column(String(50))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    generation_time_ms = Column(Integer)
    version = Column(Integer, server_default="1", nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="content")
    listing = relationship("Listing", back_populates="content")
    user = relationship("User", back_populates="content")
    brand_profile = relationship("BrandProfile", back_populates="content")
    versions = relationship("ContentVersion", back_populates="content", cascade="all, delete-orphan")
