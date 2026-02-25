"""add social_posts table for Meta Graph API tracking

Tracks Facebook and Instagram post attempts per tenant: platform,
body, photo URL, success/failure, and platform post ID. Ported from
gor-marketing's file-based social post logs.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-02-25 23:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "social_posts",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("content_id", sa.UUID(), nullable=True),
        sa.Column("listing_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(2000), nullable=True),
        sa.Column("link_url", sa.String(2000), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("platform_post_id", sa.String(200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
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
    op.create_index("ix_social_posts_tenant_id", "social_posts", ["tenant_id"])
    op.create_index(
        "ix_social_posts_tenant_created", "social_posts", ["tenant_id", "created_at"]
    )
    op.create_index(
        "ix_social_posts_tenant_listing", "social_posts", ["tenant_id", "listing_id"]
    )
    op.create_index(
        "ix_social_posts_tenant_platform", "social_posts", ["tenant_id", "platform"]
    )


def downgrade() -> None:
    op.drop_index("ix_social_posts_tenant_platform", table_name="social_posts")
    op.drop_index("ix_social_posts_tenant_listing", table_name="social_posts")
    op.drop_index("ix_social_posts_tenant_created", table_name="social_posts")
    op.drop_index("ix_social_posts_tenant_id", table_name="social_posts")
    op.drop_table("social_posts")
