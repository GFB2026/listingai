"""Email campaign tracking for send history and deliverability auditing.

Each row represents one email send operation (which may target multiple
recipients via SendGrid personalizations). Stores delivery results for
debugging, analytics, and CAN-SPAM compliance.
"""

import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class EmailCampaign(Base, TenantMixin, TimestampMixin):
    __tablename__ = "email_campaigns"

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

    # What was sent
    subject = Column(String(500), nullable=False)
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(200))
    reply_to = Column(String(255))
    recipient_count = Column(Integer, nullable=False, default=0)
    html_body = Column(Text)

    # Delivery results
    sent = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    errors = Column(JSONB, default=list)

    # Campaign type: just_listed, open_house, price_reduction, just_sold, agent_notify, custom
    campaign_type = Column(String(30), nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    content = relationship("Content")
    listing = relationship("Listing")
    user = relationship("User")

    __table_args__ = (
        Index("ix_email_campaigns_tenant_created", "tenant_id", "created_at"),
        Index("ix_email_campaigns_tenant_listing", "tenant_id", "listing_id"),
    )
