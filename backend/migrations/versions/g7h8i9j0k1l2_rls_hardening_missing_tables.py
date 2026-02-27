"""rls_hardening_missing_tables

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-02-25 12:00:00.000000

Extends the RLS policies from a1b2c3d4e5f6 to cover all multi-tenant tables
added after the original migration:
  - agent_pages
  - leads
  - email_campaigns
  - social_posts
  - page_visits

Also creates a restricted ``listingai_app`` DB role and applies FORCE ROW LEVEL
SECURITY on all tenant-scoped tables so RLS cannot be bypassed even if the
connection uses the table-owner role.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that already have RLS from the original migration.
EXISTING_RLS_TABLES = [
    "users",
    "listings",
    "content",
    "brand_profiles",
    "mls_connections",
    "usage_events",
]

# Tables added after the original migration that need RLS policies.
NEW_RLS_TABLES = [
    "agent_pages",
    "leads",
    "email_campaigns",
    "social_posts",
    "page_visits",
]

ALL_RLS_TABLES = EXISTING_RLS_TABLES + NEW_RLS_TABLES


def upgrade() -> None:
    # ---------------------------------------------------------------
    # 1. Add RLS policies to newly added multi-tenant tables
    # ---------------------------------------------------------------
    for table in NEW_RLS_TABLES:
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

    # ---------------------------------------------------------------
    # 2. Create restricted application role (idempotent)
    # ---------------------------------------------------------------
    # The role gets SELECT/INSERT/UPDATE/DELETE on all tables but
    # NOT the ability to bypass RLS (no BYPASSRLS, no superuser).
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'listingai_app') THEN
                CREATE ROLE listingai_app LOGIN NOINHERIT;
            END IF;
        END
        $$;
    """)

    # Grant table-level privileges so the app role can read/write rows
    # (RLS policies still filter what it can see).
    for table in ALL_RLS_TABLES + ["tenants", "content_versions", "lead_activities"]:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO listingai_app")

    # Grant usage on sequences so INSERT with serial/identity columns works.
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO listingai_app")

    # ---------------------------------------------------------------
    # 3. FORCE RLS on all tenant-scoped tables
    # ---------------------------------------------------------------
    # FORCE means RLS applies even to the table owner, providing
    # defense-in-depth in case the connection uses the owner role.
    for table in ALL_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # ---------------------------------------------------------------
    # Revert FORCE back to regular ENABLE on existing tables
    # ---------------------------------------------------------------
    for table in EXISTING_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")

    # ---------------------------------------------------------------
    # Drop RLS policies and disable RLS on new tables
    # ---------------------------------------------------------------
    for table in NEW_RLS_TABLES:
        for action in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # ---------------------------------------------------------------
    # Revoke grants and drop restricted role
    # ---------------------------------------------------------------
    for table in ALL_RLS_TABLES + ["tenants", "content_versions", "lead_activities"]:
        op.execute(f"REVOKE SELECT, INSERT, UPDATE, DELETE ON {table} FROM listingai_app")
    op.execute("REVOKE USAGE ON ALL SEQUENCES IN SCHEMA public FROM listingai_app")
    op.execute("DROP ROLE IF EXISTS listingai_app")
