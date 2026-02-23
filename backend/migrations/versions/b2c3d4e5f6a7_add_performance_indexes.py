"""add performance indexes

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Login lookups — users searched by email before tenant_id is known
    op.create_index("ix_users_email", "users", ["email"])

    # 2. MLS sync filtering — sync_engine filters listings by connection
    op.create_index("ix_listings_mls_connection_id", "listings", ["mls_connection_id"])

    # 3. Content list default sort — most endpoints ORDER BY created_at DESC
    op.create_index("ix_content_tenant_created", "content", ["tenant_id", sa.text("created_at DESC")])

    # 4. City filter — listings endpoint WHERE address_city ILIKE
    op.create_index("ix_listings_tenant_city", "listings", ["tenant_id", "address_city"])

    # 5. Default brand profile lookup — service layer queries WHERE is_default = true
    op.create_index("ix_brand_profiles_tenant_default", "brand_profiles", ["tenant_id", "is_default"])


def downgrade() -> None:
    op.drop_index("ix_brand_profiles_tenant_default", table_name="brand_profiles")
    op.drop_index("ix_listings_tenant_city", table_name="listings")
    op.drop_index("ix_content_tenant_created", table_name="content")
    op.drop_index("ix_listings_mls_connection_id", table_name="listings")
    op.drop_index("ix_users_email", table_name="users")
