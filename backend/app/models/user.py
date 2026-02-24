import uuid

from sqlalchemy import Boolean, Column, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class User(Base, TenantMixin, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(20), server_default="agent", nullable=False)  # admin, broker, agent
    api_key_hash = Column(String(255))
    api_key_prefix = Column(String(10))
    is_active = Column(Boolean, server_default=text("true"), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    content = relationship("Content", back_populates="user")
    agent_page = relationship("AgentPage", back_populates="user", uselist=False)

    __table_args__ = (
        {"schema": None},
    )

    # Unique constraint on (tenant_id, email) added via migration
