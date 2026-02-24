import uuid

from sqlalchemy import Column, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class PageVisit(Base, TenantMixin, TimestampMixin):
    __tablename__ = "page_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_page_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id = Column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"),
    )
    session_id = Column(String(100))

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

    # Relationships
    agent_page = relationship("AgentPage", back_populates="page_visits")

    __table_args__ = (
        Index("ix_page_visits_agent_created", "agent_page_id", "created_at"),
    )
