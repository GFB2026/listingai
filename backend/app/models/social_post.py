"""Social media post tracking for audit and analytics.

Each row represents one post attempt to a platform (Facebook or Instagram).
Stores the platform post ID on success for later reference/deletion.
"""

import uuid

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class SocialPost(Base, TenantMixin, TimestampMixin):
    __tablename__ = "social_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(
        UUID(as_uuid=True),
        ForeignKey("content.id", ondelete="SET NULL"),
    )
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Platform: facebook, instagram
    platform = Column(String(20), nullable=False)

    # What was posted
    body = Column(Text)
    photo_url = Column(String(2000))
    link_url = Column(String(2000))

    # Result
    status = Column(String(20), nullable=False)  # success, failed
    platform_post_id = Column(String(200))
    error = Column(Text)

    # Relationships
    tenant = relationship("Tenant")
    content = relationship("Content")
    listing = relationship("Listing")
    user = relationship("User")

    __table_args__ = (
        Index("ix_social_posts_tenant_created", "tenant_id", "created_at"),
        Index("ix_social_posts_tenant_listing", "tenant_id", "listing_id"),
        Index("ix_social_posts_tenant_platform", "tenant_id", "platform"),
    )
