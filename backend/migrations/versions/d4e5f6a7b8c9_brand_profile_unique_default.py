"""enforce single default brand profile per tenant

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-24 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Data fix: if any tenant has >1 default brand profile, keep only the most recently updated
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY tenant_id
                       ORDER BY updated_at DESC NULLS LAST, created_at DESC
                   ) AS rn
            FROM brand_profiles
            WHERE is_default = true
        )
        UPDATE brand_profiles
        SET is_default = false
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
    """)

    # Partial unique index: at most one default per tenant
    op.create_index(
        "ix_brand_profiles_one_default_per_tenant",
        "brand_profiles",
        ["tenant_id"],
        unique=True,
        postgresql_where="is_default = true",
    )


def downgrade() -> None:
    op.drop_index("ix_brand_profiles_one_default_per_tenant", table_name="brand_profiles")
