"""add composite index on usage_events for credit lookups

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-02-26 10:00:00.000000

Adds a composite index on (tenant_id, event_type, created_at) to speed up
the monthly credit-remaining query in ContentService.get_remaining_credits().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_usage_events_tenant_type_created",
        "usage_events",
        ["tenant_id", "event_type", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_events_tenant_type_created", table_name="usage_events")
