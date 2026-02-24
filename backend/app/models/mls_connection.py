import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, LargeBinary, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TenantMixin


class MLSConnection(Base, TenantMixin):
    __tablename__ = "mls_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)  # trestle, bridge, spark
    name = Column(String(100))
    base_url = Column(String(500), nullable=False)
    client_id_encrypted = Column(LargeBinary, nullable=False)
    client_secret_encrypted = Column(LargeBinary, nullable=False)
    access_token_encrypted = Column(LargeBinary)
    token_expires_at = Column(DateTime(timezone=True))
    sync_enabled = Column(Boolean, server_default=text("true"), nullable=False)
    last_sync_at = Column(DateTime(timezone=True))
    sync_watermark = Column(String(50))
    settings = Column(JSONB, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="mls_connections")
    listings = relationship("Listing", back_populates="mls_connection")
