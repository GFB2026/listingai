"""Tests for content CRUD endpoints: list, get, update, delete, export, generate."""
import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models.content import Content
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers


class TestListContent:
    async def test_list_content_empty(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/content", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == []
        assert data["total"] == 0

    async def test_list_content_with_data(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/content", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["content"][0]["content_type"] == "listing_description"

    async def test_list_content_filter_type(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            "/api/v1/content?content_type=listing_description", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp2 = await client.get(
            "/api/v1/content?content_type=social_instagram", headers=headers
        )
        assert resp2.json()["total"] == 0

    async def test_list_content_filter_listing(
        self, client: AsyncClient, test_user: User, test_content: Content, test_listing: Listing
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            f"/api/v1/content?listing_id={test_listing.id}", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_list_content_filter_status(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get("/api/v1/content?status=draft", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp2 = await client.get("/api/v1/content?status=published", headers=headers)
        assert resp2.json()["total"] == 0


class TestGetContent:
    async def test_get_content_success(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(f"/api/v1/content/{test_content.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(test_content.id)
        assert data["body"] == "A stunning oceanfront property with panoramic views..."

    async def test_get_content_not_found(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(f"/api/v1/content/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404


class TestUpdateContent:
    async def test_update_content_body(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/content/{test_content.id}",
            headers=headers,
            json={"body": "Updated property description with new details."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["body"] == "Updated property description with new details."
        assert data["version"] == 2  # Version should have incremented

    async def test_update_content_status(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.patch(
            f"/api/v1/content/{test_content.id}",
            headers=headers,
            json={"status": "published"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "published"
        assert data["version"] == 1  # No version bump for status-only change


class TestDeleteContent:
    async def test_delete_content(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/content/{test_content.id}", headers=headers)
        assert resp.status_code == 204

        # Verify it's gone
        resp2 = await client.get(f"/api/v1/content/{test_content.id}", headers=headers)
        assert resp2.status_code == 404

    async def test_delete_content_not_found(
        self, client: AsyncClient, test_user: User
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.delete(f"/api/v1/content/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404


class TestExportContent:
    async def test_export_txt(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            f"/api/v1/content/{test_content.id}/export/txt", headers=headers
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"
        assert "content-disposition" in resp.headers
        assert resp.text == "A stunning oceanfront property with panoramic views..."

    async def test_export_html(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            f"/api/v1/content/{test_content.id}/export/html", headers=headers
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "<!DOCTYPE html>" in resp.text

    async def test_export_invalid_format(
        self, client: AsyncClient, test_user: User, test_content: Content
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        resp = await client.get(
            f"/api/v1/content/{test_content.id}/export/csv", headers=headers
        )
        assert resp.status_code == 400


class TestGenerateContent:
    async def test_generate_content_mocked(
        self, client: AsyncClient, test_user: User, test_listing: Listing, test_tenant: Tenant
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        mock_result = {
            "body": "Discover this stunning 3-bedroom condo with breathtaking ocean views.",
            "model": "claude-sonnet-4-5-20250929",
            "metadata": {"word_count": 12},
            "prompt_tokens": 100,
            "completion_tokens": 50,
        }
        with patch(
            "app.api.v1.content.AIService.generate",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await client.post(
                "/api/v1/content/generate",
                headers=headers,
                json={
                    "listing_id": str(test_listing.id),
                    "content_type": "listing_description",
                    "tone": "professional",
                    "variants": 1,
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["content"]) == 1
        assert "ocean views" in data["content"][0]["body"]
        assert "credits_consumed" in data["usage"]

    async def test_generate_insufficient_credits(
        self,
        client: AsyncClient,
        test_user: User,
        test_listing: Listing,
        test_tenant: Tenant,
    ):
        headers = await auth_headers(client, "test@example.com", "testpassword123")
        with patch(
            "app.api.v1.content.ContentService.get_remaining_credits",
            new_callable=AsyncMock,
            return_value=0,
        ):
            resp = await client.post(
                "/api/v1/content/generate",
                headers=headers,
                json={
                    "listing_id": str(test_listing.id),
                    "content_type": "listing_description",
                    "tone": "professional",
                    "variants": 1,
                },
            )
        assert resp.status_code == 402
        assert "Insufficient credits" in resp.json()["detail"]
