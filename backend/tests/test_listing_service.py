"""Tests for ListingService.upsert_from_mls — update and create paths."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.models.mls_connection import MLSConnection
from app.models.tenant import Tenant
from app.services.listing_service import ListingService


def _make_connection(db_session: AsyncSession, tenant: Tenant) -> MLSConnection:
    """Create a real MLSConnection to satisfy FK constraints."""
    conn = MLSConnection(
        tenant_id=tenant.id,
        provider="trestle",
        name="Test MLS",
        base_url="https://api-trestle.example.com",
        client_id_encrypted=b"encrypted_id",
        client_secret_encrypted=b"encrypted_secret",
    )
    db_session.add(conn)
    return conn


class TestUpsertFromMls:
    @pytest.mark.asyncio
    async def test_create_new_listing(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(db_session, test_tenant)
        await db_session.flush()

        service = ListingService(db_session)

        mls_data = {
            "mls_listing_id": "MLS-001",
            "status": "active",
            "property_type": "condo",
            "address_full": "100 Ocean Blvd, Fort Lauderdale, FL 33308",
            "address_street": "100 Ocean Blvd",
            "address_city": "Fort Lauderdale",
            "address_state": "FL",
            "address_zip": "33308",
            "price": 750000,
            "bedrooms": 2,
            "bathrooms": 2,
            "sqft": 1500,
        }

        listing, is_new = await service.upsert_from_mls(
            tenant_id=test_tenant.id,
            mls_connection_id=conn.id,
            mls_data=mls_data,
        )

        assert is_new is True
        assert listing.mls_listing_id == "MLS-001"
        assert listing.price == 750000
        assert listing.tenant_id == test_tenant.id

    @pytest.mark.asyncio
    async def test_update_existing_listing(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(db_session, test_tenant)
        await db_session.flush()

        # Create initial listing
        listing = Listing(
            tenant_id=test_tenant.id,
            mls_connection_id=conn.id,
            mls_listing_id="MLS-002",
            status="active",
            property_type="condo",
            address_full="200 Beach Rd",
            address_street="200 Beach Rd",
            address_city="Miami",
            address_state="FL",
            address_zip="33139",
            price=500000,
            bedrooms=1,
            bathrooms=1,
            sqft=800,
        )
        db_session.add(listing)
        await db_session.flush()

        service = ListingService(db_session)

        # Upsert with updated price
        mls_data = {
            "mls_listing_id": "MLS-002",
            "price": 525000,
            "status": "pending",
        }

        updated, is_new = await service.upsert_from_mls(
            tenant_id=test_tenant.id,
            mls_connection_id=conn.id,
            mls_data=mls_data,
        )

        assert is_new is False
        assert updated.id == listing.id  # Same record
        assert updated.price == 525000
        assert updated.status == "pending"
        # Unchanged field should remain
        assert updated.address_city == "Miami"

    @pytest.mark.asyncio
    async def test_update_skips_none_values(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(db_session, test_tenant)
        await db_session.flush()

        listing = Listing(
            tenant_id=test_tenant.id,
            mls_connection_id=conn.id,
            mls_listing_id="MLS-003",
            status="active",
            property_type="residential",
            address_full="300 Main St",
            address_street="300 Main St",
            address_city="Tampa",
            address_state="FL",
            address_zip="33601",
            price=400000,
            bedrooms=3,
            bathrooms=2,
            sqft=1800,
        )
        db_session.add(listing)
        await db_session.flush()

        service = ListingService(db_session)

        # Update with None values — should not overwrite
        mls_data = {
            "mls_listing_id": "MLS-003",
            "price": None,
            "status": "sold",
        }

        updated, is_new = await service.upsert_from_mls(
            tenant_id=test_tenant.id,
            mls_connection_id=conn.id,
            mls_data=mls_data,
        )

        assert is_new is False
        assert updated.price == 400000  # Not overwritten by None
        assert updated.status == "sold"
