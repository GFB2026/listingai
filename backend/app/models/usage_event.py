import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.base import TenantMixin


class UsageEvent(Base, TenantMixin):
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    event_type = Column(String(50), nullable=False)  # content_generation, mls_sync, export
    content_type = Column(String(30))
    tokens_used = Column(Integer, default=0)
    credits_consumed = Column(Integer, default=1)
    stripe_reported = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
