"""Tests for content API endpoints — generate, regenerate, batch, list, update, delete."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.content import Content
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.user import User


def _auth_token(user: User, tenant: Tenant) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def _mock_ai_result():
    return {
        "body": "Beautiful waterfront property.",
        "model": "claude-sonnet-4-5-20250929",
        "prompt_tokens": 150,
        "completion_tokens": 50,
        "metadata": {"word_count": 3},
    }


class TestGenerateContent:
    @pytest.mark.asyncio
    async def test_listing_not_found(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.post(
            "/api/v1/content/generate",
            headers=headers,
            json={
                "listing_id": str(uuid4()),
                "content_type": "listing_description",
                "tone": "professional",
            },
        )
        assert response.status_code == 404
        assert "Listing not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_brand_profile_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        test_listing: Listing,
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.post(
            "/api/v1/content/generate",
            headers=headers,
            json={
                "listing_id": str(test_listing.id),
                "content_type": "listing_description",
                "tone": "professional",
                "brand_profile_id": str(uuid4()),
            },
        )
        assert response.status_code == 404
        assert "Brand profile not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
        test_listing: Listing,
    ):
        headers = _auth_token(test_user, test_tenant)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(return_value=_mock_ai_result())

        with patch("app.api.v1.content.AIService", return_value=mock_ai):
            response = await client.post(
                "/api/v1/content/generate",
                headers=headers,
                json={
                    "listing_id": str(test_listing.id),
                    "content_type": "listing_description",
                    "tone": "professional",
                    "variants": 1,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data["content"]) == 1
        assert data["content"][0]["body"] == "Beautiful waterfront property."
        assert data["usage"]["credits_consumed"] == 1

    @pytest.mark.asyncio
    async def test_generate_multiple_variants(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
        test_listing: Listing,
    ):
        headers = _auth_token(test_user, test_tenant)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(return_value=_mock_ai_result())

        with patch("app.api.v1.content.AIService", return_value=mock_ai):
            response = await client.post(
                "/api/v1/content/generate",
                headers=headers,
                json={
                    "listing_id": str(test_listing.id),
                    "content_type": "listing_description",
                    "tone": "luxury",
                    "variants": 3,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data["content"]) == 3
        assert data["usage"]["credits_consumed"] == 3


class TestRegenerateContent:
    @pytest.mark.asyncio
    async def test_regenerate_not_found(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.post(
            f"/api/v1/content/{uuid4()}/regenerate",
            headers=headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_regenerate_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
        test_content: Content,
    ):
        headers = _auth_token(test_user, test_tenant)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(return_value=_mock_ai_result())

        with patch("app.api.v1.content.AIService", return_value=mock_ai):
            response = await client.post(
                f"/api/v1/content/{test_content.id}/regenerate",
                headers=headers,
            )

        assert response.status_code == 200
        assert response.json()["body"] == "Beautiful waterfront property."


class TestBatchGenerate:
    @pytest.mark.asyncio
    async def test_batch_queued(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        test_listing: Listing,
    ):
        headers = _auth_token(test_user, test_tenant)

        with patch(
            "app.workers.tasks.content_batch.batch_generate_content"
        ) as mock_task:
            mock_task.delay = MagicMock()
            response = await client.post(
                "/api/v1/content/batch",
                headers=headers,
                json={
                    "listing_ids": [str(test_listing.id)],
                    "content_type": "listing_description",
                    "tone": "professional",
                },
            )

        assert response.status_code == 202
        data = response.json()
        assert data["listing_count"] == 1


class TestUpdateContent:
    @pytest.mark.asyncio
    async def test_update_body_creates_version(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
        test_content: Content,
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.patch(
            f"/api/v1/content/{test_content.id}",
            headers=headers,
            json={"body": "Updated content body"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["body"] == "Updated content body"
        assert data["version"] == 2  # incremented from 1

    @pytest.mark.asyncio
    async def test_update_status(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        test_content: Content,
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.patch(
            f"/api/v1/content/{test_content.id}",
            headers=headers,
            json={"status": "published"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "published"


class TestDeleteContent:
    @pytest.mark.asyncio
    async def test_delete(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        test_content: Content,
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.delete(
            f"/api/v1/content/{test_content.id}", headers=headers
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        headers = _auth_token(test_user, test_tenant)
        response = await client.delete(
            f"/api/v1/content/{uuid4()}", headers=headers
        )
        assert response.status_code == 404
