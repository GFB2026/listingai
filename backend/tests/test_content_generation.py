"""Tests for content generation endpoint including credit enforcement and AI service."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.user import User
from app.services.content_service import ContentService


class TestContentService:
    @pytest.mark.asyncio
    async def test_get_remaining_credits(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        service = ContentService(db_session)
        remaining = await service.get_remaining_credits(test_tenant.id)
        # Professional plan = 1000 credits, no usage yet
        assert remaining == 1000

    @pytest.mark.asyncio
    async def test_create_content(
        self, db_session: AsyncSession, test_tenant: Tenant, test_user: User
    ):
        # First create a listing
        listing = Listing(
            tenant_id=test_tenant.id,
            address_full="123 Test St, Miami, FL",
            address_city="Miami",
            address_state="FL",
            price=Decimal("500000"),
            bedrooms=3,
            bathrooms=Decimal("2"),
            sqft=1500,
            property_type="residential",
            status="active",
        )
        db_session.add(listing)
        await db_session.flush()

        service = ContentService(db_session)
        content = await service.create(
            tenant_id=test_tenant.id,
            listing_id=listing.id,
            user_id=test_user.id,
            content_type="listing_description",
            tone="professional",
            body="A beautiful property",
            metadata={"word_count": 3},
            ai_model="claude-sonnet-4-5-20250929",
            prompt_tokens=100,
            completion_tokens=50,
            generation_time_ms=1500,
        )

        assert content.id is not None
        assert content.body == "A beautiful property"
        assert content.content_type == "listing_description"
        assert content.prompt_tokens == 100

    @pytest.mark.asyncio
    async def test_track_usage(
        self, db_session: AsyncSession, test_tenant: Tenant, test_user: User
    ):
        service = ContentService(db_session)

        # Track usage
        await service.track_usage(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            content_type="listing_description",
            count=5,
            tokens=500,
        )
        await db_session.flush()

        # Remaining should reflect the usage
        remaining = await service.get_remaining_credits(test_tenant.id)
        assert remaining == 995  # 1000 - 5


class TestCreditEnforcement:
    @pytest.mark.asyncio
    async def test_generate_rejected_when_over_limit(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, test_tenant: Tenant
    ):
        # Set a very low limit
        test_tenant.monthly_generation_limit = 0
        db_session.add(test_tenant)
        await db_session.flush()

        # Create a listing
        listing = Listing(
            tenant_id=test_tenant.id,
            address_full="123 Test St",
            address_city="Miami",
            address_state="FL",
            price=Decimal("500000"),
            bedrooms=3,
            bathrooms=Decimal("2"),
            sqft=1500,
            property_type="residential",
            status="active",
        )
        db_session.add(listing)
        await db_session.flush()

        token = create_access_token(
            data={
                "sub": str(test_user.id),
                "tenant_id": str(test_tenant.id),
                "role": "admin",
            }
        )

        response = await client.post(
            "/api/v1/content/generate",
            json={
                "listing_id": str(listing.id),
                "content_type": "listing_description",
                "tone": "professional",
                "variants": 1,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 402
        assert "Insufficient credits" in response.json()["detail"]


class TestAIService:
    @pytest.mark.asyncio
    async def test_generate_calls_claude(self):
        """Verify the AI service makes a call to Claude and returns structured data."""
        from app.services.ai_service import AIService

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Beautiful waterfront property.")]
        mock_response.usage.input_tokens = 150
        mock_response.usage.output_tokens = 50

        listing = MagicMock()
        listing.address_full = "4250 Galt Ocean Dr"
        listing.price = 1500000
        listing.bedrooms = 3
        listing.bathrooms = 2.5
        listing.sqft = 2200
        listing.property_type = "condo"
        listing.year_built = 2020
        listing.features = ["Ocean View"]
        listing.description_original = None
        listing.listing_agent_name = None

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        with patch.object(AIService, "__init__", lambda self: None):
            service = AIService()
            service.client = AsyncMock()
            service.client.messages.create = AsyncMock(return_value=mock_response)
            from app.services.prompt_builder import PromptBuilder
            service.prompt_builder = PromptBuilder()

            # Also reset circuit breaker for clean test
            from app.services import ai_service
            ai_service._circuit = ai_service._CircuitBreaker()

            result = await service.generate(
                listing=listing,
                content_type="listing_description",
                tone="luxury",
                brand_profile_id=None,
                instructions=None,
                tenant_id=str(uuid4()),
                db=db,
            )

        assert result["body"] == "Beautiful waterfront property."
        assert result["model"] == "claude-sonnet-4-5-20250929"
        assert result["prompt_tokens"] == 150
        assert result["completion_tokens"] == 50
        assert result["metadata"]["word_count"] == 3

    @pytest.mark.asyncio
    async def test_generate_circuit_breaker_blocks_when_open(self):
        """When the circuit breaker is open, generate should raise CircuitBreakerOpen."""
        from app.services.ai_service import AIService, CircuitBreakerOpen, _CircuitBreaker
        from app.services import ai_service

        # Force circuit open
        cb = _CircuitBreaker(threshold=1, recovery=300)
        cb.record_failure()
        ai_service._circuit = cb

        listing = MagicMock()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        with patch.object(AIService, "__init__", lambda self: None):
            service = AIService()
            service.prompt_builder = MagicMock()
            service.prompt_builder.build = MagicMock(return_value=("system", "user"))
            service.client = AsyncMock()

            with pytest.raises(CircuitBreakerOpen):
                await service.generate(
                    listing=listing,
                    content_type="listing_description",
                    tone="professional",
                    brand_profile_id=None,
                    instructions=None,
                    tenant_id=str(uuid4()),
                    db=db,
                )

        # Reset for other tests
        ai_service._circuit = _CircuitBreaker()
