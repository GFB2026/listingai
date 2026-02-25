"""add email_campaigns table for send tracking

Tracks email delivery operations: subject, recipients, delivery results,
and campaign type. Supports multi-tenant isolation and links to content,
listing, and user records. Ported from gor-marketing's file-based
email send logs.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-02-25 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_campaigns",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("content_id", sa.UUID(), nullable=True),
        sa.Column("listing_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("from_email", sa.String(255), nullable=False),
        sa.Column("from_name", sa.String(200), nullable=True),
        sa.Column("reply_to", sa.String(255), nullable=True),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("campaign_type", sa.String(30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_email_campaigns_tenant_id", "email_campaigns", ["tenant_id"])
    op.create_index(
        "ix_email_campaigns_tenant_created", "email_campaigns", ["tenant_id", "created_at"]
    )
    op.create_index(
        "ix_email_campaigns_tenant_listing", "email_campaigns", ["tenant_id", "listing_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_email_campaigns_tenant_listing", table_name="email_campaigns")
    op.drop_index("ix_email_campaigns_tenant_created", table_name="email_campaigns")
    op.drop_index("ix_email_campaigns_tenant_id", table_name="email_campaigns")
    op.drop_table("email_campaigns")
