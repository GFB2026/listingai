from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import String, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_page import AgentPage
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.models.page_visit import PageVisit
from app.models.tenant import Tenant
from app.models.user import User


VALID_STATUSES = {"new", "contacted", "showing", "under_contract", "closed", "lost"}

PIPELINE_ORDER = ["new", "contacted", "showing", "under_contract", "closed", "lost"]


class LeadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Public: resolve tenant + agent page from slugs ──────────

    async def resolve_agent_page(
        self, tenant_slug: str, agent_slug: str,
    ) -> tuple[Tenant, AgentPage] | None:
        """Look up tenant and agent page by slugs. Returns None if not found."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        result = await self.db.execute(
            select(AgentPage).where(
                AgentPage.tenant_id == tenant.id,
                AgentPage.slug == agent_slug,
                AgentPage.is_active.is_(True),
            )
        )
        agent_page = result.scalar_one_or_none()
        if not agent_page:
            return None

        return tenant, agent_page

    # ── Public: create lead ─────────────────────────────────────

    async def create_lead_public(
        self,
        tenant: Tenant,
        agent_page: AgentPage,
        *,
        first_name: str,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        message: str | None = None,
        property_interest: str | None = None,
        listing_id: UUID | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
        utm_term: str | None = None,
        referrer_url: str | None = None,
        landing_url: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Lead:
        lead = Lead(
            tenant_id=tenant.id,
            agent_page_id=agent_page.id,
            agent_id=agent_page.user_id,
            listing_id=listing_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            message=message,
            property_interest=property_interest,
            pipeline_status="new",
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            referrer_url=referrer_url,
            landing_url=landing_url,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(lead)
        await self.db.flush()

        # Create initial activity
        activity = LeadActivity(
            lead_id=lead.id,
            activity_type="status_change",
            new_value="new",
            note="Lead submitted via landing page",
        )
        self.db.add(activity)

        return lead

    # ── Public: record visit ────────────────────────────────────

    async def record_visit(
        self,
        tenant: Tenant,
        agent_page: AgentPage,
        *,
        listing_id: UUID | None = None,
        session_id: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
        utm_term: str | None = None,
        referrer_url: str | None = None,
        landing_url: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PageVisit:
        visit = PageVisit(
            tenant_id=tenant.id,
            agent_page_id=agent_page.id,
            listing_id=listing_id,
            session_id=session_id,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            referrer_url=referrer_url,
            landing_url=landing_url,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(visit)
        await self.db.flush()
        return visit

    # ── Authenticated: list leads ───────────────────────────────

    async def list_leads(
        self,
        tenant_id: UUID,
        *,
        agent_id: UUID | None = None,
        pipeline_status: str | None = None,
        utm_source: str | None = None,
        page: int = 1,
        page_size: int = 20,
        user_role: str = "agent",
        current_user_id: UUID | None = None,
    ) -> tuple[list[Lead], int]:
        query = select(Lead).where(Lead.tenant_id == tenant_id)

        # Agents see only their own leads
        if user_role == "agent" and current_user_id:
            query = query.where(Lead.agent_id == current_user_id)
        elif agent_id:
            query = query.where(Lead.agent_id == agent_id)

        if pipeline_status:
            query = query.where(Lead.pipeline_status == pipeline_status)
        if utm_source:
            query = query.where(Lead.utm_source == utm_source)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Paginate
        query = query.order_by(Lead.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        leads = result.scalars().all()

        return leads, total

    # ── Authenticated: update lead ──────────────────────────────

    async def update_lead(
        self,
        lead: Lead,
        user: User,
        *,
        pipeline_status: str | None = None,
        closed_value=None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        property_interest: str | None = None,
    ) -> Lead:
        if pipeline_status and pipeline_status != lead.pipeline_status:
            if pipeline_status not in VALID_STATUSES:
                raise ValueError(f"Invalid status: {pipeline_status}")
            old_status = lead.pipeline_status
            lead.pipeline_status = pipeline_status

            # Record status change activity
            activity = LeadActivity(
                lead_id=lead.id,
                user_id=user.id,
                activity_type="status_change",
                old_value=old_status,
                new_value=pipeline_status,
            )
            self.db.add(activity)

            # Set closed_at when moving to closed
            if pipeline_status == "closed":
                lead.closed_at = datetime.now(UTC)

        if closed_value is not None:
            lead.closed_value = closed_value
        if first_name is not None:
            lead.first_name = first_name
        if last_name is not None:
            lead.last_name = last_name
        if email is not None:
            lead.email = email
        if phone is not None:
            lead.phone = phone
        if property_interest is not None:
            lead.property_interest = property_interest

        self.db.add(lead)
        return lead

    # ── Authenticated: add activity ─────────────────────────────

    async def add_activity(
        self,
        lead: Lead,
        user: User,
        *,
        activity_type: str,
        note: str | None = None,
    ) -> LeadActivity:
        activity = LeadActivity(
            lead_id=lead.id,
            user_id=user.id,
            activity_type=activity_type,
            note=note,
        )
        self.db.add(activity)
        await self.db.flush()
        return activity

    # ── Analytics ───────────────────────────────────────────────

    async def get_summary(self, tenant_id: UUID) -> dict:
        # Total leads
        total_result = await self.db.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == tenant_id)
        )
        total = total_result.scalar()

        # By status
        status_result = await self.db.execute(
            select(Lead.pipeline_status, func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .group_by(Lead.pipeline_status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # By source
        direct_label = literal("direct", String)
        source_result = await self.db.execute(
            select(
                func.coalesce(Lead.utm_source, direct_label),
                func.count(Lead.id),
            )
            .where(Lead.tenant_id == tenant_id)
            .group_by(func.coalesce(Lead.utm_source, direct_label))
        )
        by_source = {row[0]: row[1] for row in source_result.all()}

        # By agent
        agent_result = await self.db.execute(
            select(
                User.full_name,
                User.id,
                func.count(Lead.id),
            )
            .join(User, Lead.agent_id == User.id)
            .where(Lead.tenant_id == tenant_id)
            .group_by(User.id, User.full_name)
            .order_by(func.count(Lead.id).desc())
        )
        by_agent = [
            {"agent_name": row[0], "agent_id": str(row[1]), "count": row[2]}
            for row in agent_result.all()
        ]

        # Total closed value
        closed_result = await self.db.execute(
            select(func.sum(Lead.closed_value))
            .where(Lead.tenant_id == tenant_id, Lead.pipeline_status == "closed")
        )
        total_closed = closed_result.scalar()

        return {
            "total_leads": total,
            "by_status": by_status,
            "by_source": by_source,
            "by_agent": by_agent,
            "total_closed_value": total_closed,
        }

    async def get_funnel(self, tenant_id: UUID) -> tuple[list[dict], int]:
        total_result = await self.db.execute(
            select(func.count(Lead.id)).where(Lead.tenant_id == tenant_id)
        )
        total = total_result.scalar() or 0

        status_result = await self.db.execute(
            select(Lead.pipeline_status, func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .group_by(Lead.pipeline_status)
        )
        counts = {row[0]: row[1] for row in status_result.all()}

        funnel = []
        for status in PIPELINE_ORDER:
            count = counts.get(status, 0)
            percentage = (count / total * 100) if total > 0 else 0
            funnel.append({
                "status": status,
                "count": count,
                "percentage": round(percentage, 1),
            })

        return funnel, total
