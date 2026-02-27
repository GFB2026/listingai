"""create least-privilege application database role

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-02-27 10:00:00.000000

Creates a restricted ``listingai_app`` PostgreSQL role with the minimum
privileges required to run the application:

  - CONNECT on the database
  - USAGE on the ``public`` schema (no CREATE — cannot alter DDL)
  - SELECT, INSERT, UPDATE, DELETE on all current tables
  - USAGE, SELECT on all sequences (for auto-increment primary keys)
  - ALTER DEFAULT PRIVILEGES so future tables/sequences created by the
    migration owner are automatically accessible to the app role

The role explicitly does NOT receive:
  - CREATE on any schema (cannot create or drop tables)
  - TRUNCATE on any table
  - SUPERUSER, CREATEDB, CREATEROLE, BYPASSRLS
  - A password (set externally via ``ALTER ROLE listingai_app PASSWORD '...'``)

The earlier migration g7h8i9j0k1l2 already creates the role and grants
per-table DML.  This migration layers on the database-level and schema-level
grants plus default privileges that were missing, making the role fully
self-contained and future-proof.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Every table in the application as of this migration.
# The g7h8i9j0k1l2 migration already grants per-table DML on most of these;
# we re-issue the grants here so this migration is self-contained and safe to
# run even if the earlier per-table grants are ever removed.
# ---------------------------------------------------------------------------
ALL_TABLES = [
    "tenants",
    "users",
    "listings",
    "content",
    "content_versions",
    "brand_profiles",
    "email_campaigns",
    "mls_connections",
    "usage_events",
    "agent_pages",
    "leads",
    "lead_activities",
    "page_visits",
    "social_posts",
]


def upgrade() -> None:
    # -----------------------------------------------------------------
    # 1. Ensure the role exists (idempotent)
    # -----------------------------------------------------------------
    # NOINHERIT    — does not inherit privileges from granted roles
    # NOCREATEDB   — cannot create databases
    # NOCREATEROLE — cannot create other roles
    # NOBYPASSRLS  — subject to row-level security policies
    # NOSUPERUSER  — not a superuser (implicit, but explicit for clarity)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'listingai_app') THEN
                CREATE ROLE listingai_app
                    LOGIN
                    NOINHERIT
                    NOCREATEDB
                    NOCREATEROLE
                    NOSUPERUSER
                    NOBYPASSRLS;
            END IF;
        END
        $$;
    """)

    # -----------------------------------------------------------------
    # 2. Database-level: CONNECT only
    #    current_database() cannot be used directly in GRANT, so we
    #    use dynamic SQL inside a DO block.
    # -----------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO listingai_app',
                           current_database());
        END
        $$;
    """)

    # -----------------------------------------------------------------
    # 3. Schema-level: USAGE only (no CREATE)
    # -----------------------------------------------------------------
    op.execute("GRANT USAGE ON SCHEMA public TO listingai_app")

    # -----------------------------------------------------------------
    # 4. Table-level: SELECT, INSERT, UPDATE, DELETE on all tables
    #    (explicitly no TRUNCATE, REFERENCES, or TRIGGER)
    # -----------------------------------------------------------------
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON ALL TABLES IN SCHEMA public "
        "TO listingai_app"
    )

    # -----------------------------------------------------------------
    # 5. Sequence-level: USAGE and SELECT on all sequences
    # -----------------------------------------------------------------
    op.execute(
        "GRANT USAGE, SELECT "
        "ON ALL SEQUENCES IN SCHEMA public "
        "TO listingai_app"
    )

    # -----------------------------------------------------------------
    # 6. Default privileges for future objects
    #    These ensure that tables/sequences created by future migrations
    #    (running as the owner role) are automatically accessible.
    # -----------------------------------------------------------------
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON TABLES TO listingai_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT "
        "ON SEQUENCES TO listingai_app"
    )


def downgrade() -> None:
    # -----------------------------------------------------------------
    # 1. Revoke default privileges
    # -----------------------------------------------------------------
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE "
        "ON TABLES FROM listingai_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE USAGE, SELECT "
        "ON SEQUENCES FROM listingai_app"
    )

    # -----------------------------------------------------------------
    # 2. Revoke sequence privileges
    # -----------------------------------------------------------------
    op.execute(
        "REVOKE USAGE, SELECT "
        "ON ALL SEQUENCES IN SCHEMA public "
        "FROM listingai_app"
    )

    # -----------------------------------------------------------------
    # 3. Revoke table privileges
    # -----------------------------------------------------------------
    op.execute(
        "REVOKE SELECT, INSERT, UPDATE, DELETE "
        "ON ALL TABLES IN SCHEMA public "
        "FROM listingai_app"
    )

    # -----------------------------------------------------------------
    # 4. Revoke schema and database privileges
    # -----------------------------------------------------------------
    op.execute("REVOKE USAGE ON SCHEMA public FROM listingai_app")
    op.execute("""
        DO $$
        BEGIN
            EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM listingai_app',
                           current_database());
        END
        $$;
    """)

    # -----------------------------------------------------------------
    # 5. Drop the role (only if no other objects depend on it)
    # -----------------------------------------------------------------
    op.execute("DROP ROLE IF EXISTS listingai_app")
