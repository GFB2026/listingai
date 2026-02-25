"""add agent contact and sale metadata fields to listings

Adds listing_agent_email, listing_agent_phone, previous_price, close_price,
and close_date columns. These are ported from gor-marketing to support
event-specific content (price_reduction, just_sold) and email sign-offs
with real agent contact info.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-25 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("listing_agent_email", sa.String(255), nullable=True))
    op.add_column("listings", sa.Column("listing_agent_phone", sa.String(30), nullable=True))
    op.add_column(
        "listings", sa.Column("previous_price", sa.Numeric(12, 2), nullable=True)
    )
    op.add_column("listings", sa.Column("close_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("listings", sa.Column("close_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "close_date")
    op.drop_column("listings", "close_price")
    op.drop_column("listings", "previous_price")
    op.drop_column("listings", "listing_agent_phone")
    op.drop_column("listings", "listing_agent_email")
