"""Tests for brand profile API endpoints: list, create, update, delete."""

import uuid

from httpx import AsyncClient

from app.models.brand_profile import BrandProfile
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


class TestListBrandProfiles:
    async def test_list_profiles_empty(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/brand-profiles", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_profiles(
        self, client: AsyncClient, test_user: User, test_brand_profile: BrandProfile
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/brand-profiles", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Luxury Coastal"
        assert data[0]["is_default"] is True


class TestCreateBrandProfile:
    async def test_create_profile(self, client: AsyncClient, test_user: User, test_tenant: Tenant):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.post(
            "/api/v1/brand-profiles",
            headers=headers,
            json={
                "name": "Modern Minimal",
                "voice_description": "Clean, modern, minimalist tone",
                "vocabulary": ["sleek", "modern", "curated"],
                "avoid_words": ["old-fashioned"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Modern Minimal"
        assert data["is_default"] is False

    async def test_create_profile_default_unsets_others(
        self, client: AsyncClient, test_user: User, test_brand_profile: BrandProfile
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        # Create a new profile as default — should unset test_brand_profile
        resp = await client.post(
            "/api/v1/brand-profiles",
            headers=headers,
            json={
                "name": "New Default",
                "is_default": True,
                "voice_description": "The new default voice",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["is_default"] is True

        # Verify the old default is no longer default
        list_resp = await client.get("/api/v1/brand-profiles", headers=headers)
        profiles = list_resp.json()
        defaults = [p for p in profiles if p["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "New Default"

    async def test_create_profile_validation(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        # Missing required name
        resp = await client.post("/api/v1/brand-profiles", headers=headers, json={})
        assert resp.status_code == 422


class TestUpdateBrandProfile:
    async def test_update_profile(
        self, client: AsyncClient, test_user: User, test_brand_profile: BrandProfile
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/brand-profiles/{test_brand_profile.id}",
            headers=headers,
            json={"name": "Updated Coastal", "voice_description": "Updated description"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Coastal"
        assert data["voice_description"] == "Updated description"

    async def test_update_profile_to_default_unsets_others(
        self, client: AsyncClient, test_user: User, test_brand_profile: BrandProfile
    ):
        """Updating a profile to is_default=True should unset others."""
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        # Create a second non-default profile
        resp = await client.post(
            "/api/v1/brand-profiles",
            headers=headers,
            json={"name": "Second Voice", "voice_description": "Second"},
        )
        assert resp.status_code == 201
        second_id = resp.json()["id"]

        # Update the second profile to be default
        resp = await client.patch(
            f"/api/v1/brand-profiles/{second_id}",
            headers=headers,
            json={"is_default": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_default"] is True

        # Verify only one default exists
        list_resp = await client.get("/api/v1/brand-profiles", headers=headers)
        profiles = list_resp.json()
        defaults = [p for p in profiles if p["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["id"] == second_id

    async def test_update_profile_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/brand-profiles/{uuid.uuid4()}",
            headers=headers,
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404


class TestDeleteBrandProfile:
    async def test_delete_profile(
        self, client: AsyncClient, test_user: User, test_brand_profile: BrandProfile
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(
            f"/api/v1/brand-profiles/{test_brand_profile.id}", headers=headers
        )
        assert resp.status_code == 204

        # Verify it's gone
        list_resp = await client.get("/api/v1/brand-profiles", headers=headers)
        assert list_resp.json() == []

    async def test_delete_profile_not_found(self, client: AsyncClient, test_user: User):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/brand-profiles/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404


class TestBrandProfileAuth:
    async def test_profile_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/brand-profiles")
        assert resp.status_code in (401, 403)
