"""Tests for Row-Level Security tenant isolation.

Verifies that set_tenant_context properly sets the PostgreSQL session variable
and that application-level tenant-scoped queries filter correctly.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import set_tenant_context
from app.models.brand_profile import BrandProfile
from app.models.listing import Listing
from app.models.tenant import Tenant


class TestSetTenantContext:
    @pytest.mark.asyncio
    async def test_sets_session_variable(self, db_session: AsyncSession, test_tenant: Tenant):
        """Verify current_setting('app.current_tenant_id') returns the set value."""
        await set_tenant_context(db_session, str(test_tenant.id))

        result = await db_session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        value = result.scalar()
        assert value == str(test_tenant.id)

    @pytest.mark.asyncio
    async def test_context_is_transaction_scoped(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """Verify context resets after commit (set_config with is_local=true)."""
        await set_tenant_context(db_session, str(test_tenant.id))
        await db_session.commit()

        # After commit, the transaction-local setting should be gone
        result = await db_session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        value = result.scalar()
        # Should be empty string or None after transaction ends
        assert value in (None, "")


class TestTenantScopedQueries:
    @pytest.mark.asyncio
    async def test_queries_filter_by_tenant(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        other_tenant: Tenant,
    ):
        """Application-level WHERE tenant_id = ... returns only matching tenant's data."""
        # Create a listing for each tenant
        listing_a = Listing(
            tenant_id=test_tenant.id,
            address_full="100 Ocean Blvd, Fort Lauderdale, FL 33308",
            address_street="100 Ocean Blvd",
            address_city="Fort Lauderdale",
            address_state="FL",
            address_zip="33308",
            price=500000,
            bedrooms=2,
            bathrooms=2,
            sqft=1200,
            property_type="condo",
            status="active",
        )
        listing_b = Listing(
            tenant_id=other_tenant.id,
            address_full="200 Beach Rd, Miami, FL 33139",
            address_street="200 Beach Rd",
            address_city="Miami",
            address_state="FL",
            address_zip="33139",
            price=750000,
            bedrooms=3,
            bathrooms=2,
            sqft=1800,
            property_type="house",
            status="active",
        )
        db_session.add_all([listing_a, listing_b])
        await db_session.flush()

        # Query filtered to test_tenant should return only listing_a
        result = await db_session.execute(
            select(Listing).where(Listing.tenant_id == test_tenant.id)
        )
        listings = result.scalars().all()
        assert len(listings) == 1
        assert listings[0].id == listing_a.id

        # Query filtered to other_tenant should return only listing_b
        result = await db_session.execute(
            select(Listing).where(Listing.tenant_id == other_tenant.id)
        )
        listings = result.scalars().all()
        assert len(listings) == 1
        assert listings[0].id == listing_b.id

    @pytest.mark.asyncio
    async def test_brand_profiles_isolated_by_tenant(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        other_tenant: Tenant,
    ):
        """Brand profiles for one tenant are not visible when querying another."""
        bp_a = BrandProfile(
            tenant_id=test_tenant.id,
            name="Tenant A Voice",
            voice_description="Voice A",
        )
        bp_b = BrandProfile(
            tenant_id=other_tenant.id,
            name="Tenant B Voice",
            voice_description="Voice B",
        )
        db_session.add_all([bp_a, bp_b])
        await db_session.flush()

        # Query for test_tenant's profiles only
        result = await db_session.execute(
            select(BrandProfile).where(BrandProfile.tenant_id == test_tenant.id)
        )
        profiles = result.scalars().all()
        assert len(profiles) == 1
        assert profiles[0].name == "Tenant A Voice"

        # Query for other_tenant's profiles only
        result = await db_session.execute(
            select(BrandProfile).where(BrandProfile.tenant_id == other_tenant.id)
        )
        profiles = result.scalars().all()
        assert len(profiles) == 1
        assert profiles[0].name == "Tenant B Voice"
