"""harden_schema_constraints_rls

Revision ID: a1b2c3d4e5f6
Revises: cbe7f3435501
Create Date: 2026-02-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "cbe7f3435501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that get RLS policies (have tenant_id column, excluding tenants itself
# and content_versions which is protected by FK cascade from content).
RLS_TABLES = [
    "users",
    "listings",
    "content",
    "brand_profiles",
    "mls_connections",
    "usage_events",
]


def upgrade() -> None:
    # ---------------------------------------------------------------
    # 2a. Backfill NULL values (must happen before NOT NULL constraints)
    # ---------------------------------------------------------------
    op.execute("UPDATE tenants SET plan = 'free' WHERE plan IS NULL")
    op.execute("UPDATE tenants SET monthly_generation_limit = 50 WHERE monthly_generation_limit IS NULL")
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE users SET role = 'agent' WHERE role IS NULL")
    op.execute("UPDATE brand_profiles SET is_default = false WHERE is_default IS NULL")
    op.execute("UPDATE mls_connections SET sync_enabled = true WHERE sync_enabled IS NULL")
    op.execute("UPDATE usage_events SET stripe_reported = false WHERE stripe_reported IS NULL")
    op.execute("UPDATE content SET status = 'draft' WHERE status IS NULL")
    op.execute("UPDATE content SET version = 1 WHERE version IS NULL")
    op.execute("UPDATE listings SET status = 'active' WHERE status IS NULL")

    # ---------------------------------------------------------------
    # 2b. Add server defaults + NOT NULL
    # ---------------------------------------------------------------

    # tenants.plan
    op.alter_column("tenants", "plan",
                    existing_type=sa.String(50),
                    server_default="free",
                    nullable=False)
    # tenants.monthly_generation_limit
    op.alter_column("tenants", "monthly_generation_limit",
                    existing_type=sa.Integer(),
                    server_default="50",
                    nullable=False)
    # users.is_active
    op.alter_column("users", "is_active",
                    existing_type=sa.Boolean(),
                    server_default=sa.text("true"),
                    nullable=False)
    # users.role
    op.alter_column("users", "role",
                    existing_type=sa.String(20),
                    server_default="agent",
                    nullable=False)
    # brand_profiles.is_default
    op.alter_column("brand_profiles", "is_default",
                    existing_type=sa.Boolean(),
                    server_default=sa.text("false"),
                    nullable=False)
    # mls_connections.sync_enabled
    op.alter_column("mls_connections", "sync_enabled",
                    existing_type=sa.Boolean(),
                    server_default=sa.text("true"),
                    nullable=False)
    # usage_events.stripe_reported
    op.alter_column("usage_events", "stripe_reported",
                    existing_type=sa.Boolean(),
                    server_default=sa.text("false"),
                    nullable=False)
    # content.status
    op.alter_column("content", "status",
                    existing_type=sa.String(20),
                    server_default="draft",
                    nullable=False)
    # content.version
    op.alter_column("content", "version",
                    existing_type=sa.Integer(),
                    server_default="1",
                    nullable=False)
    # listings.status
    op.alter_column("listings", "status",
                    existing_type=sa.String(20),
                    server_default="active",
                    nullable=False)

    # ---------------------------------------------------------------
    # 2c. CHECK constraints
    # ---------------------------------------------------------------
    op.create_check_constraint(
        "ck_tenants_plan", "tenants",
        "plan IN ('free','starter','professional','enterprise')")
    op.create_check_constraint(
        "ck_users_role", "users",
        "role IN ('admin','broker','agent')")
    op.create_check_constraint(
        "ck_listings_status", "listings",
        "status IN ('active','pending','sold','withdrawn','expired','coming_soon')")
    op.create_check_constraint(
        "ck_listings_price_positive", "listings",
        "price >= 0")
    op.create_check_constraint(
        "ck_listings_bedrooms_positive", "listings",
        "bedrooms >= 0")
    op.create_check_constraint(
        "ck_listings_bathrooms_positive", "listings",
        "bathrooms >= 0")
    op.create_check_constraint(
        "ck_listings_sqft_positive", "listings",
        "sqft >= 0")
    op.create_check_constraint(
        "ck_listings_lot_sqft_positive", "listings",
        "lot_sqft >= 0")
    op.create_check_constraint(
        "ck_listings_year_built_range", "listings",
        "year_built BETWEEN 1600 AND 2100")
    op.create_check_constraint(
        "ck_content_status", "content",
        "status IN ('draft','approved','published','archived')")
    op.create_check_constraint(
        "ck_content_type", "content",
        "content_type IN ('description','social_instagram','social_facebook','social_x','email','flyer','video_script')")
    op.create_check_constraint(
        "ck_content_version_positive", "content",
        "version >= 1")
    op.create_check_constraint(
        "ck_cv_version_positive", "content_versions",
        "version >= 1")
    op.create_check_constraint(
        "ck_usage_event_type", "usage_events",
        "event_type IN ('content_generation','mls_sync','export')")
    op.create_check_constraint(
        "ck_mls_provider", "mls_connections",
        "provider IN ('trestle','bridge','spark')")

    # ---------------------------------------------------------------
    # 2d. UNIQUE constraints and indexes
    # ---------------------------------------------------------------

    # Unique email per tenant
    op.create_unique_constraint(
        "uq_users_tenant_email", "users",
        ["tenant_id", "email"])

    # Unique MLS listing ID per tenant (partial index — only where mls_listing_id IS NOT NULL)
    op.execute(
        "CREATE UNIQUE INDEX ix_listings_tenant_mls_id "
        "ON listings (tenant_id, mls_listing_id) "
        "WHERE mls_listing_id IS NOT NULL"
    )

    # Unique version per content item
    op.create_unique_constraint(
        "uq_content_versions_content_version", "content_versions",
        ["content_id", "version"])

    # FK lookup index for content_versions
    op.create_index("ix_content_versions_content_id", "content_versions", ["content_id"])

    # Billing time-range queries
    op.create_index("ix_usage_events_tenant_created", "usage_events", ["tenant_id", "created_at"])

    # Listing detail content lookups
    op.create_index("ix_content_tenant_listing", "content", ["tenant_id", "listing_id"])

    # Filtered list queries
    op.create_index("ix_listings_tenant_status", "listings", ["tenant_id", "status"])

    # ---------------------------------------------------------------
    # 2e. Row-Level Security
    # ---------------------------------------------------------------
    # Using ENABLE (not FORCE) so the table owner (migration user) bypasses RLS.
    # The app user is subject to policies when connecting as a non-owner role.
    # NOTE: The restricted `listingai_app` role is created in migration
    # g7h8i9j0k1l2 (role + per-table grants + FORCE RLS) and hardened with
    # database/schema-level grants + default privileges in i9j0k1l2m3n4.
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_select ON {table} "
            f"FOR SELECT USING (tenant_id = current_setting('app.current_tenant_id')::uuid)"
        )
        op.execute(
            f"CREATE POLICY tenant_isolation_insert ON {table} "
            f"FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)"
        )
        op.execute(
            f"CREATE POLICY tenant_isolation_update ON {table} "
            f"FOR UPDATE USING (tenant_id = current_setting('app.current_tenant_id')::uuid)"
        )
        op.execute(
            f"CREATE POLICY tenant_isolation_delete ON {table} "
            f"FOR DELETE USING (tenant_id = current_setting('app.current_tenant_id')::uuid)"
        )


def downgrade() -> None:
    # ---------------------------------------------------------------
    # Drop RLS policies and disable RLS
    # ---------------------------------------------------------------
    for table in RLS_TABLES:
        for action in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # ---------------------------------------------------------------
    # Drop indexes and constraints
    # ---------------------------------------------------------------
    op.drop_index("ix_listings_tenant_status", table_name="listings")
    op.drop_index("ix_content_tenant_listing", table_name="content")
    op.drop_index("ix_usage_events_tenant_created", table_name="usage_events")
    op.drop_index("ix_content_versions_content_id", table_name="content_versions")
    op.execute("DROP INDEX IF EXISTS ix_listings_tenant_mls_id")
    op.drop_constraint("uq_content_versions_content_version", "content_versions", type_="unique")
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")

    # ---------------------------------------------------------------
    # Drop CHECK constraints
    # ---------------------------------------------------------------
    op.drop_constraint("ck_mls_provider", "mls_connections", type_="check")
    op.drop_constraint("ck_usage_event_type", "usage_events", type_="check")
    op.drop_constraint("ck_cv_version_positive", "content_versions", type_="check")
    op.drop_constraint("ck_content_version_positive", "content", type_="check")
    op.drop_constraint("ck_content_type", "content", type_="check")
    op.drop_constraint("ck_content_status", "content", type_="check")
    op.drop_constraint("ck_listings_year_built_range", "listings", type_="check")
    op.drop_constraint("ck_listings_lot_sqft_positive", "listings", type_="check")
    op.drop_constraint("ck_listings_sqft_positive", "listings", type_="check")
    op.drop_constraint("ck_listings_bathrooms_positive", "listings", type_="check")
    op.drop_constraint("ck_listings_bedrooms_positive", "listings", type_="check")
    op.drop_constraint("ck_listings_price_positive", "listings", type_="check")
    op.drop_constraint("ck_listings_status", "listings", type_="check")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_constraint("ck_tenants_plan", "tenants", type_="check")

    # ---------------------------------------------------------------
    # Restore columns to nullable with no defaults
    # ---------------------------------------------------------------
    op.alter_column("listings", "status",
                    existing_type=sa.String(20),
                    server_default=None, nullable=True)
    op.alter_column("content", "version",
                    existing_type=sa.Integer(),
                    server_default=None, nullable=True)
    op.alter_column("content", "status",
                    existing_type=sa.String(20),
                    server_default=None, nullable=True)
    op.alter_column("usage_events", "stripe_reported",
                    existing_type=sa.Boolean(),
                    server_default=None, nullable=True)
    op.alter_column("mls_connections", "sync_enabled",
                    existing_type=sa.Boolean(),
                    server_default=None, nullable=True)
    op.alter_column("brand_profiles", "is_default",
                    existing_type=sa.Boolean(),
                    server_default=None, nullable=True)
    op.alter_column("users", "role",
                    existing_type=sa.String(20),
                    server_default=None, nullable=True)
    op.alter_column("users", "is_active",
                    existing_type=sa.Boolean(),
                    server_default=None, nullable=True)
    op.alter_column("tenants", "monthly_generation_limit",
                    existing_type=sa.Integer(),
                    server_default=None, nullable=True)
    op.alter_column("tenants", "plan",
                    existing_type=sa.String(50),
                    server_default=None, nullable=True)
