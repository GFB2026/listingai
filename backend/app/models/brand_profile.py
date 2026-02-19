import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin


class BrandProfile(Base, TenantMixin):
    __tablename__ = "brand_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    voice_description = Column(Text)
    vocabulary = Column(JSONB, default=list)
    avoid_words = Column(JSONB, default=list)
    sample_content = Column(Text)
    settings = Column(JSONB, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="brand_profiles")
    content = relationship("Content", back_populates="brand_profile")
