from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_profile import BrandProfile
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.services.ai_service import AIService, _CircuitBreaker
from app.services.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def test_build_listing_section(self):
        builder = PromptBuilder()

        listing = MagicMock()
        listing.address_full = "4250 Galt Ocean Dr, Fort Lauderdale, FL 33308"
        listing.price = 1500000
        listing.bedrooms = 3
        listing.bathrooms = 2.5
        listing.sqft = 2200
        listing.property_type = "condo"
        listing.year_built = 2020
        listing.features = ["Ocean View", "Pool", "Renovated Kitchen"]
        listing.description_original = "Beautiful ocean view condo"
        listing.listing_agent_name = "Dennis Test"

        result = builder._build_listing_section(listing)

        assert "4250 Galt Ocean Dr" in result
        assert "$1,500,000" in result
        assert "3BR" in result
        assert "2.5BA" in result
        assert "2,200" in result
        assert "Ocean View" in result

    def test_build_brand_section(self):
        builder = PromptBuilder()

        profile = MagicMock()
        profile.voice_description = "Luxury and sophisticated"
        profile.vocabulary = ["coastal", "exclusive", "premier"]
        profile.avoid_words = ["cheap", "deal"]
        profile.sample_content = "Experience the finest in coastal living."

        result = builder._build_brand_section(profile)

        assert "BRAND VOICE:" in result
        assert "Luxury and sophisticated" in result
        assert "coastal" in result
        assert "cheap" in result

    def test_build_returns_system_and_user_prompts(self):
        builder = PromptBuilder()

        listing = MagicMock()
        listing.address_full = "123 Test St"
        listing.price = 500000
        listing.bedrooms = 2
        listing.bathrooms = 1
        listing.sqft = 1000
        listing.property_type = "residential"
        listing.year_built = 2010
        listing.features = []
        listing.description_original = None
        listing.listing_agent_name = None

        system, user = builder.build(
            listing=listing,
            content_type="social_instagram",
            tone="luxury",
        )

        assert "Instagram" in system
        assert "luxury" in system
        assert "123 Test St" in user
        assert "Generate the content now." in user


class TestAIServiceGenerate:
    """Test AIService.generate — brand profile loading and API call paths."""

    def _mock_listing(self):
        listing = MagicMock(spec=Listing)
        listing.address_full = "100 Ocean Blvd"
        listing.price = 1000000
        listing.bedrooms = 3
        listing.bathrooms = 2
        listing.sqft = 2000
        listing.property_type = "condo"
        listing.year_built = 2020
        listing.features = ["Pool"]
        listing.description_original = "Nice condo"
        listing.listing_agent_name = "Agent"
        return listing

    def _mock_response(self, text="Generated content here"):
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        resp.usage = MagicMock(input_tokens=100, output_tokens=50)
        return resp

    @pytest.mark.asyncio
    async def test_generate_with_brand_profile_id(
        self, db_session: AsyncSession, test_tenant: Tenant, test_brand_profile: BrandProfile
    ):
        """When brand_profile_id is provided, it should be loaded from DB."""
        listing = self._mock_listing()
        mock_resp = self._mock_response()

        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()
            service.client = MagicMock()
            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(return_value=mock_resp)

            # Reset circuit breaker
            from app.services.ai_service import _circuit
            _circuit._state = "closed"
            _circuit._failure_count = 0

            result = await service.generate(
                listing=listing,
                content_type="listing_description",
                tone="professional",
                brand_profile_id=str(test_brand_profile.id),
                instructions=None,
                tenant_id=str(test_tenant.id),
                db=db_session,
            )

        assert result["body"] == "Generated content here"
        assert result["prompt_tokens"] == 100

    @pytest.mark.asyncio
    async def test_generate_api_connection_error(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        listing = self._mock_listing()

        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()
            service.client = MagicMock()
            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(
                side_effect=anthropic.APIConnectionError(request=MagicMock())
            )

            from app.services.ai_service import _circuit
            _circuit._state = "closed"
            _circuit._failure_count = 0

            with pytest.raises(anthropic.APIConnectionError):
                await service.generate(
                    listing=listing,
                    content_type="listing_description",
                    tone="professional",
                    brand_profile_id=None,
                    instructions=None,
                    tenant_id=str(test_tenant.id),
                    db=db_session,
                )

    @pytest.mark.asyncio
    async def test_generate_api_status_error_5xx(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        listing = self._mock_listing()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}

        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()
            service.client = MagicMock()
            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(
                side_effect=anthropic.APIStatusError(
                    "Internal Server Error",
                    response=mock_response,
                    body={"error": {"message": "server error"}},
                )
            )

            from app.services.ai_service import _circuit
            _circuit._state = "closed"
            _circuit._failure_count = 0

            with pytest.raises(anthropic.APIStatusError):
                await service.generate(
                    listing=listing,
                    content_type="listing_description",
                    tone="professional",
                    brand_profile_id=None,
                    instructions=None,
                    tenant_id=str(test_tenant.id),
                    db=db_session,
                )

            # 5xx should count toward circuit breaker
            assert _circuit._failure_count >= 1

    @pytest.mark.asyncio
    async def test_generate_api_status_error_4xx_no_circuit_break(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        listing = self._mock_listing()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {}

        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()
            service.client = MagicMock()
            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(
                side_effect=anthropic.APIStatusError(
                    "Bad Request",
                    response=mock_response,
                    body={"error": {"message": "bad request"}},
                )
            )

            from app.services.ai_service import _circuit
            _circuit._state = "closed"
            _circuit._failure_count = 0

            with pytest.raises(anthropic.APIStatusError):
                await service.generate(
                    listing=listing,
                    content_type="listing_description",
                    tone="professional",
                    brand_profile_id=None,
                    instructions=None,
                    tenant_id=str(test_tenant.id),
                    db=db_session,
                )

            # 4xx should NOT count toward circuit breaker
            assert _circuit._failure_count == 0


class TestExtractMetadata:
    def test_word_count(self):
        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()

        meta = service._extract_metadata("Hello world test", "listing_description")
        assert meta["word_count"] == 3
        assert meta["character_count"] == 16

    def test_hashtags_for_social(self):
        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()

        meta = service._extract_metadata(
            "Check out this listing! #RealEstate #ForSale #Miami", "social_instagram"
        )
        assert "#RealEstate" in meta["hashtags"]
        assert "#ForSale" in meta["hashtags"]
        assert "#Miami" in meta["hashtags"]
        assert len(meta["hashtags"]) == 3

    def test_no_hashtags_for_non_social(self):
        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()

        meta = service._extract_metadata("Body with #tag", "listing_description")
        assert "hashtags" not in meta


class TestMarketDataInGenerate:
    """Test that tenant market data flows through AIService.generate into prompts."""

    def _mock_listing(self):
        listing = MagicMock(spec=Listing)
        listing.address_full = "100 Ocean Blvd, Fort Lauderdale, FL 33308"
        listing.address_city = "Fort Lauderdale"
        listing.address_zip = "33308"
        listing.county = None
        listing.price = 1000000
        listing.bedrooms = 3
        listing.bathrooms = 2
        listing.sqft = 2000
        listing.property_type = "condo"
        listing.year_built = 2020
        listing.features = ["Pool"]
        listing.description_original = "Nice condo"
        listing.listing_agent_name = "Agent"
        listing.listing_agent_email = None
        listing.listing_agent_phone = None
        return listing

    def _mock_response(self, text="Generated content here"):
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        resp.usage = MagicMock(input_tokens=100, output_tokens=50)
        return resp

    @pytest.mark.asyncio
    async def test_generate_includes_market_data_from_tenant_settings(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """When tenant has market_data in settings, it should be passed to prompt builder."""
        # Set market data on tenant
        test_tenant.settings = {
            "market_data": {
                "areas": [
                    {
                        "name": "Beach Zone",
                        "zip_codes": ["33308"],
                        "stats": {
                            "median_price": 500000,
                            "median_dom": 45,
                            "months_supply": 3.5,
                        },
                    }
                ]
            }
        }
        db_session.add(test_tenant)
        await db_session.flush()

        listing = self._mock_listing()
        mock_resp = self._mock_response()

        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()
            service.client = MagicMock()
            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(return_value=mock_resp)

            from app.services.ai_service import _circuit
            _circuit._state = "closed"
            _circuit._failure_count = 0

            # Spy on prompt builder to verify market_areas is passed
            original_build = service.prompt_builder.build
            build_calls = []

            def capture_build(*args, **kwargs):
                build_calls.append(kwargs)
                return original_build(*args, **kwargs)

            service.prompt_builder.build = capture_build

            result = await service.generate(
                listing=listing,
                content_type="listing_description",
                tone="professional",
                brand_profile_id=None,
                instructions=None,
                tenant_id=str(test_tenant.id),
                db=db_session,
            )

        assert result["body"] == "Generated content here"
        assert len(build_calls) == 1
        assert build_calls[0]["market_areas"] is not None
        assert len(build_calls[0]["market_areas"]) == 1
        assert build_calls[0]["market_areas"][0]["name"] == "Beach Zone"

        # Verify the API was called with market context in the user prompt
        call_kwargs = service.client.messages.create.call_args[1]
        user_message = call_kwargs["messages"][0]["content"]
        assert "MARKET CONTEXT:" in user_message
        assert "$500,000" in user_message

    @pytest.mark.asyncio
    async def test_generate_without_market_data_still_works(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """When tenant has no market data, generation should proceed normally."""
        # Ensure tenant has no settings
        test_tenant.settings = {}
        db_session.add(test_tenant)
        await db_session.flush()

        listing = self._mock_listing()
        mock_resp = self._mock_response()

        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()
            service.client = MagicMock()
            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(return_value=mock_resp)

            from app.services.ai_service import _circuit
            _circuit._state = "closed"
            _circuit._failure_count = 0

            result = await service.generate(
                listing=listing,
                content_type="listing_description",
                tone="professional",
                brand_profile_id=None,
                instructions=None,
                tenant_id=str(test_tenant.id),
                db=db_session,
            )

        assert result["body"] == "Generated content here"
        # Verify no market context in the prompt
        call_kwargs = service.client.messages.create.call_args[1]
        user_message = call_kwargs["messages"][0]["content"]
        assert "MARKET CONTEXT:" not in user_message

    @pytest.mark.asyncio
    async def test_generate_with_null_tenant_settings(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """When tenant.settings is None, generation should proceed normally."""
        test_tenant.settings = None
        db_session.add(test_tenant)
        await db_session.flush()

        listing = self._mock_listing()
        mock_resp = self._mock_response()

        with patch("app.services.ai_service.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "sk-test"
            service = AIService()
            service.client = MagicMock()
            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(return_value=mock_resp)

            from app.services.ai_service import _circuit
            _circuit._state = "closed"
            _circuit._failure_count = 0

            result = await service.generate(
                listing=listing,
                content_type="listing_description",
                tone="professional",
                brand_profile_id=None,
                instructions=None,
                tenant_id=str(test_tenant.id),
                db=db_session,
            )

        assert result["body"] == "Generated content here"


class TestCircuitBreakerHalfOpen:
    def test_half_open_blocks_second_request(self):
        cb = _CircuitBreaker(threshold=2, recovery=1)
        cb._set_state("half_open")
        # Half-open should return False (only one probe allowed)
        assert cb.allow_request() is False
