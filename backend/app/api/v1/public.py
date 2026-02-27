"""Public endpoints for landing pages, lead capture, and visit tracking.

No authentication required. Rate-limited and CSRF-exempt.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.agent_page import AgentPage
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.schemas.lead import LeadCreate, PageVisitCreate
from app.services.lead_service import LeadService

router = APIRouter()


def _client_ip(request: Request) -> str:
    """Extract client IP, validating X-Forwarded-For format."""
    import ipaddress

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        candidate = forwarded.split(",")[0].strip()
        # Validate it looks like an IP address (prevent header injection)
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass  # Fall through to direct client IP
    return request.client.host if request.client else "unknown"


@router.get("/pages/{tenant_slug}/{agent_slug}")
async def get_agent_page(
    tenant_slug: str,
    agent_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Public agent landing page data + active listings."""
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Page not found")

    result = await db.execute(
        select(AgentPage)
        .options(selectinload(AgentPage.user))
        .where(
            AgentPage.tenant_id == tenant.id,
            AgentPage.slug == agent_slug,
            AgentPage.is_active.is_(True),
        )
    )
    agent_page = result.scalar_one_or_none()
    if not agent_page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Fetch active listings for this agent
    result = await db.execute(
        select(Listing).where(
            Listing.tenant_id == tenant.id,
            Listing.listing_agent_id == agent_page.user_id,
            Listing.status == "active",
        ).order_by(Listing.created_at.desc()).limit(20)
    )
    listings = result.scalars().all()

    return {
        "agent": {
            "slug": agent_page.slug,
            "headline": agent_page.headline,
            "bio": agent_page.bio,
            "photo_url": agent_page.photo_url,
            "phone": agent_page.phone,
            "email": agent_page.email_display,
            "theme": agent_page.theme,
            "name": agent_page.user.full_name if agent_page.user else None,
        },
        "brokerage": {
            "name": tenant.name,
            "slug": tenant.slug,
        },
        "listings": [
            {
                "id": str(listing.id),
                "address_full": listing.address_full,
                "price": float(listing.price) if listing.price else None,
                "bedrooms": listing.bedrooms,
                "bathrooms": float(listing.bathrooms) if listing.bathrooms else None,
                "sqft": listing.sqft,
                "photos": listing.photos or [],
                "property_type": listing.property_type,
                "status": listing.status,
            }
            for listing in listings
        ],
    }


@router.get("/pages/{tenant_slug}/{agent_slug}/listings/{listing_id}")
async def get_listing_landing(
    tenant_slug: str,
    agent_slug: str,
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Public listing-specific landing page data."""
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Page not found")

    result = await db.execute(
        select(AgentPage)
        .options(selectinload(AgentPage.user))
        .where(
            AgentPage.tenant_id == tenant.id,
            AgentPage.slug == agent_slug,
            AgentPage.is_active.is_(True),
        )
    )
    agent_page = result.scalar_one_or_none()
    if not agent_page:
        raise HTTPException(status_code=404, detail="Page not found")

    result = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.tenant_id == tenant.id,
        )
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    return {
        "agent": {
            "slug": agent_page.slug,
            "headline": agent_page.headline,
            "bio": agent_page.bio,
            "photo_url": agent_page.photo_url,
            "phone": agent_page.phone,
            "email": agent_page.email_display,
            "theme": agent_page.theme,
            "name": agent_page.user.full_name if agent_page.user else None,
        },
        "brokerage": {
            "name": tenant.name,
            "slug": tenant.slug,
        },
        "listing": {
            "id": str(listing.id),
            "address_full": listing.address_full,
            "address_city": listing.address_city,
            "address_state": listing.address_state,
            "price": float(listing.price) if listing.price else None,
            "bedrooms": listing.bedrooms,
            "bathrooms": float(listing.bathrooms) if listing.bathrooms else None,
            "sqft": listing.sqft,
            "lot_sqft": listing.lot_sqft,
            "year_built": listing.year_built,
            "description_original": listing.description_original,
            "features": listing.features or [],
            "photos": listing.photos or [],
            "property_type": listing.property_type,
            "status": listing.status,
        },
    }


@router.post("/leads", status_code=status.HTTP_201_CREATED)
async def submit_lead(
    request: Request,
    payload: LeadCreate,
    db: AsyncSession = Depends(get_db),
):
    """Public lead form submission."""
    service = LeadService(db)
    resolved = await service.resolve_agent_page(payload.tenant_slug, payload.agent_slug)
    if not resolved:
        raise HTTPException(status_code=404, detail="Agent page not found")

    tenant, agent_page = resolved

    lead = await service.create_lead_public(
        tenant,
        agent_page,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        message=payload.message,
        property_interest=payload.property_interest,
        listing_id=payload.listing_id,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
        utm_term=payload.utm_term,
        referrer_url=payload.referrer_url,
        landing_url=payload.landing_url,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", "")[:500],
    )

    return {"id": str(lead.id), "status": "received"}


@router.post("/visits", status_code=status.HTTP_201_CREATED)
async def record_visit(
    request: Request,
    payload: PageVisitCreate,
    db: AsyncSession = Depends(get_db),
):
    """Track anonymous page visits."""
    service = LeadService(db)
    resolved = await service.resolve_agent_page(payload.tenant_slug, payload.agent_slug)
    if not resolved:
        raise HTTPException(status_code=404, detail="Agent page not found")

    tenant, agent_page = resolved

    await service.record_visit(
        tenant,
        agent_page,
        listing_id=payload.listing_id,
        session_id=payload.session_id,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
        utm_term=payload.utm_term,
        referrer_url=payload.referrer_url,
        landing_url=payload.landing_url,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", "")[:500],
    )

    return {"status": "ok"}


@router.get("/link-config/{tenant_slug}")
async def get_link_config(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Agent slugs + listing IDs for gor-marketing link builder."""
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get active agent pages with user info
    result = await db.execute(
        select(AgentPage)
        .options(selectinload(AgentPage.user))
        .where(
            AgentPage.tenant_id == tenant.id,
            AgentPage.is_active.is_(True),
        )
    )
    agent_pages = result.scalars().all()

    # Get active listings
    result = await db.execute(
        select(Listing).where(
            Listing.tenant_id == tenant.id,
            Listing.status == "active",
        )
    )
    listings = result.scalars().all()

    # Build agent-to-listings mapping
    agents = []
    for page in agent_pages:
        agent_listings = [
            {
                "id": str(listing.id),
                "mls_id": listing.mls_listing_id,
                "address": listing.address_full,
            }
            for listing in listings
            if listing.listing_agent_id == page.user_id
        ]
        agents.append({
            "slug": page.slug,
            "name": page.user.full_name if page.user else None,
            "user_id": str(page.user_id),
            "listings": agent_listings,
        })

    return {
        "tenant_slug": tenant.slug,
        "agents": agents,
    }
