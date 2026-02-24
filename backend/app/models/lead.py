import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class Lead(Base, TenantMixin, TimestampMixin):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_page_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_pages.id", ondelete="SET NULL"),
    )
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )
    listing_id = Column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"),
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    email = Column(String(255))
    phone = Column(String(30))
    message = Column(Text)
    property_interest = Column(String(500))

    # Pipeline
    pipeline_status = Column(
        String(20), server_default="new", nullable=False,
    )  # new, contacted, showing, under_contract, closed, lost

    # UTM tracking
    utm_source = Column(String(200))
    utm_medium = Column(String(200))
    utm_campaign = Column(String(200))
    utm_content = Column(String(200))
    utm_term = Column(String(200))

    # Attribution
    referrer_url = Column(String(2000))
    landing_url = Column(String(2000))
    ip_address = Column(String(45))
    user_agent = Column(String(500))

    # Closing
    closed_value = Column(Numeric(12, 2))
    closed_at = Column(DateTime(timezone=True))

    # Relationships
    tenant = relationship("Tenant", back_populates="leads")
    agent_page = relationship("AgentPage", back_populates="leads")
    activities = relationship(
        "LeadActivity", back_populates="lead", cascade="all, delete-orphan",
        order_by="LeadActivity.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_leads_tenant_agent", "tenant_id", "agent_id"),
        Index("ix_leads_tenant_status", "tenant_id", "pipeline_status"),
        Index("ix_leads_tenant_created", "tenant_id", "created_at"),
    )
