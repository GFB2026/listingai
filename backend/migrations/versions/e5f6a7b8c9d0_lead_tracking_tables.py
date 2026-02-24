"""add lead tracking tables (agent_pages, leads, lead_activities, page_visits)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-24 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # agent_pages
    op.create_table(
        "agent_pages",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("headline", sa.String(255)),
        sa.Column("bio", sa.String(2000)),
        sa.Column("photo_url", sa.String(500)),
        sa.Column("phone", sa.String(30)),
        sa.Column("email_display", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("theme", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_agent_pages_tenant_slug"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_agent_pages_tenant_user"),
    )
    op.create_index("ix_agent_pages_tenant_id", "agent_pages", ["tenant_id"])

    # leads
    op.create_table(
        "leads",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_page_id", sa.UUID()),
        sa.Column("agent_id", sa.UUID()),
        sa.Column("listing_id", sa.UUID()),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(30)),
        sa.Column("message", sa.Text()),
        sa.Column("property_interest", sa.String(500)),
        sa.Column("pipeline_status", sa.String(20), server_default="new", nullable=False),
        sa.Column("utm_source", sa.String(200)),
        sa.Column("utm_medium", sa.String(200)),
        sa.Column("utm_campaign", sa.String(200)),
        sa.Column("utm_content", sa.String(200)),
        sa.Column("utm_term", sa.String(200)),
        sa.Column("referrer_url", sa.String(2000)),
        sa.Column("landing_url", sa.String(2000)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("closed_value", sa.Numeric(12, 2)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_page_id"], ["agent_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])
    op.create_index("ix_leads_tenant_agent", "leads", ["tenant_id", "agent_id"])
    op.create_index("ix_leads_tenant_status", "leads", ["tenant_id", "pipeline_status"])
    op.create_index("ix_leads_tenant_created", "leads", ["tenant_id", "created_at"])

    # lead_activities
    op.create_table(
        "lead_activities",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID()),
        sa.Column("activity_type", sa.String(30), nullable=False),
        sa.Column("old_value", sa.String(50)),
        sa.Column("new_value", sa.String(50)),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_activities_lead_id", "lead_activities", ["lead_id"])

    # page_visits
    op.create_table(
        "page_visits",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_page_id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID()),
        sa.Column("session_id", sa.String(100)),
        sa.Column("utm_source", sa.String(200)),
        sa.Column("utm_medium", sa.String(200)),
        sa.Column("utm_campaign", sa.String(200)),
        sa.Column("utm_content", sa.String(200)),
        sa.Column("utm_term", sa.String(200)),
        sa.Column("referrer_url", sa.String(2000)),
        sa.Column("landing_url", sa.String(2000)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_page_id"], ["agent_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_visits_tenant_id", "page_visits", ["tenant_id"])
    op.create_index("ix_page_visits_agent_created", "page_visits", ["agent_page_id", "created_at"])

    # RLS policies for new tables
    op.execute("""
        ALTER TABLE agent_pages ENABLE ROW LEVEL SECURITY;
        CREATE POLICY agent_pages_tenant_isolation ON agent_pages
            USING (tenant_id::text = current_setting('app.current_tenant_id', true));
    """)
    op.execute("""
        ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
        CREATE POLICY leads_tenant_isolation ON leads
            USING (tenant_id::text = current_setting('app.current_tenant_id', true));
    """)
    op.execute("""
        ALTER TABLE page_visits ENABLE ROW LEVEL SECURITY;
        CREATE POLICY page_visits_tenant_isolation ON page_visits
            USING (tenant_id::text = current_setting('app.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS page_visits_tenant_isolation ON page_visits")
    op.execute("DROP POLICY IF EXISTS leads_tenant_isolation ON leads")
    op.execute("DROP POLICY IF EXISTS agent_pages_tenant_isolation ON agent_pages")

    op.drop_table("page_visits")
    op.drop_table("lead_activities")
    op.drop_table("leads")
    op.drop_table("agent_pages")
