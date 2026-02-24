import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class AgentPage(Base, TenantMixin, TimestampMixin):
    __tablename__ = "agent_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    slug = Column(String(100), nullable=False)
    headline = Column(String(255))
    bio = Column(String(2000))
    photo_url = Column(String(500))
    phone = Column(String(30))
    email_display = Column(String(255))
    is_active = Column(Boolean, server_default="true", nullable=False)
    theme = Column(JSONB, default=dict)

    # Relationships
    tenant = relationship("Tenant", back_populates="agent_pages")
    user = relationship("User", back_populates="agent_page")
    leads = relationship("Lead", back_populates="agent_page", cascade="all, delete-orphan")
    page_visits = relationship(
        "PageVisit", back_populates="agent_page", cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_agent_pages_tenant_slug"),
        UniqueConstraint("tenant_id", "user_id", name="uq_agent_pages_tenant_user"),
    )
