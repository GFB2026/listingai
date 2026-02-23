"""Tests for listings API endpoints: list, detail, manual create, filters, pagination."""
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


class TestListListings:
    async def test_list_listings_empty(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["listings"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    async def test_list_listings_with_data(
        self, client: AsyncClient, test_user: User, test_listing: Listing
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["listings"]) == 1
        listing = data["listings"][0]
        assert listing["address_city"] == "Fort Lauderdale"
        assert listing["bedrooms"] == 3

    async def test_list_listings_pagination(
        self, client: AsyncClient, test_user: User, test_listing: Listing,
        db_session: AsyncSession, test_tenant: Tenant,
    ):
        # Add a second listing
        listing2 = Listing(
            tenant_id=test_tenant.id,
            address_full="200 Beach Dr, Miami, FL 33139",
            address_city="Miami",
            address_state="FL",
            price=800000,
            bedrooms=2,
            bathrooms=1,
            status="active",
        )
        db_session.add(listing2)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings?page=1&page_size=1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["listings"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1

    async def test_list_listings_filter_status(
        self, client: AsyncClient, test_user: User, test_listing: Listing,
        db_session: AsyncSession, test_tenant: Tenant,
    ):
        # Add a sold listing
        sold = Listing(
            tenant_id=test_tenant.id,
            address_full="300 Bay Rd, Miami, FL 33139",
            address_city="Miami",
            price=600000,
            status="sold",
        )
        db_session.add(sold)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings?status=active", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["listings"][0]["status"] == "active"

    async def test_list_listings_filter_city(
        self, client: AsyncClient, test_user: User, test_listing: Listing
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings?city=Fort", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    async def test_list_listings_filter_price_range(
        self, client: AsyncClient, test_user: User, test_listing: Listing,
        db_session: AsyncSession, test_tenant: Tenant,
    ):
        cheap = Listing(
            tenant_id=test_tenant.id,
            address_full="400 Main St, Boca Raton, FL",
            price=300000,
            status="active",
        )
        db_session.add(cheap)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            "/api/v1/listings?min_price=1000000&max_price=2000000", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert float(data["listings"][0]["price"]) == 1500000

    async def test_list_listings_filter_bedrooms(
        self, client: AsyncClient, test_user: User, test_listing: Listing,
        db_session: AsyncSession, test_tenant: Tenant,
    ):
        small = Listing(
            tenant_id=test_tenant.id,
            address_full="500 Elm St, Miami, FL",
            bedrooms=1,
            status="active",
        )
        db_session.add(small)
        await db_session.flush()

        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings?bedrooms=3", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Only the test_listing with 3 bedrooms should match (>= 3)
        assert data["total"] == 1

    async def test_list_listings_invalid_city(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings?city='; DROP TABLE--", headers=headers)
        assert resp.status_code == 400
        assert "Invalid city" in resp.json()["detail"]


class TestGetListing:
    async def test_get_listing_success(
        self, client: AsyncClient, test_user: User, test_listing: Listing
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(f"/api/v1/listings/{test_listing.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(test_listing.id)
        assert data["address_full"] == "100 Ocean Blvd, Fort Lauderdale, FL 33308"

    async def test_get_listing_not_found(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/listings/{fake_id}", headers=headers)
        assert resp.status_code == 404


class TestCreateManualListing:
    async def test_create_manual_listing(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        payload = {
            "address_full": "999 New St, Pompano Beach, FL 33062",
            "address_street": "999 New St",
            "address_city": "Pompano Beach",
            "address_state": "FL",
            "address_zip": "33062",
            "price": 750000,
            "bedrooms": 2,
            "bathrooms": 2,
            "sqft": 1500,
            "year_built": 2020,
            "property_type": "townhouse",
            "description_original": "Brand new townhouse near the beach.",
        }
        resp = await client.post("/api/v1/listings/manual", headers=headers, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["address_city"] == "Pompano Beach"
        assert data["property_type"] == "townhouse"

    async def test_create_manual_listing_validation(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        # Missing required address_full
        resp = await client.post("/api/v1/listings/manual", headers=headers, json={})
        assert resp.status_code == 422


class TestListingsAuth:
    async def test_list_listings_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/listings")
        assert resp.status_code in (401, 403)

    async def test_page_cap_enforced(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/listings?page=1001", headers=headers)
        assert resp.status_code == 422
