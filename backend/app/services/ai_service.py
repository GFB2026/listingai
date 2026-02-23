import time
from uuid import UUID

import anthropic
import httpx
import structlog
from prometheus_client import Gauge
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.brand_profile import BrandProfile
from app.models.listing import Listing
from app.services.prompt_builder import PromptBuilder

logger = structlog.get_logger()

# Circuit breaker state exposed to Prometheus: 0=closed, 1=open, 2=half_open
CIRCUIT_BREAKER_STATE = Gauge(
    "ai_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
)
_STATE_MAP = {"closed": 0, "open": 1, "half_open": 2}

# Model selection based on content type
MODEL_MAP = {
    "listing_description": "claude-sonnet-4-5-20250929",
    "social_instagram": "claude-sonnet-4-5-20250929",
    "social_facebook": "claude-sonnet-4-5-20250929",
    "social_linkedin": "claude-sonnet-4-5-20250929",
    "social_x": "claude-haiku-4-5-20251001",
    "email_just_listed": "claude-sonnet-4-5-20250929",
    "email_open_house": "claude-sonnet-4-5-20250929",
    "email_drip": "claude-sonnet-4-5-20250929",
    "flyer": "claude-sonnet-4-5-20250929",
    "video_script": "claude-sonnet-4-5-20250929",
}

# --- Circuit Breaker ---
# Simple in-process circuit breaker. Opens after FAILURE_THRESHOLD consecutive
# failures and stays open for RECOVERY_TIMEOUT seconds before allowing a probe.

FAILURE_THRESHOLD = 5
RECOVERY_TIMEOUT = 60  # seconds


class CircuitBreakerOpen(Exception):
    """Raised when the Claude API circuit breaker is open."""

    def __init__(self):
        super().__init__("AI service temporarily unavailable. Please try again shortly.")


class _CircuitBreaker:
    def __init__(self, threshold: int = FAILURE_THRESHOLD, recovery: int = RECOVERY_TIMEOUT):
        self._threshold = threshold
        self._recovery = recovery
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._state = "closed"  # closed | open | half_open

    def _set_state(self, state: str) -> None:
        self._state = state
        CIRCUIT_BREAKER_STATE.set(_STATE_MAP.get(state, 0))

    def record_success(self) -> None:
        self._failure_count = 0
        self._set_state("closed")

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._threshold:
            self._set_state("open")
            logger.warning(
                "circuit_breaker_opened",
                failures=self._failure_count,
                recovery_seconds=self._recovery,
            )

    def allow_request(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "half_open":
            return False  # Only one probe allowed; wait for success/failure result
        # state == "open"
        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self._recovery:
            self._set_state("half_open")
            return True
        return False


_circuit = _CircuitBreaker()

# Timeout for the Anthropic HTTP client (connect, read, total)
_API_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)


class AIService:
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=_API_TIMEOUT,
            max_retries=2,
        )
        self.prompt_builder = PromptBuilder()

    async def generate(
        self,
        listing: Listing,
        content_type: str,
        tone: str,
        brand_profile_id: str | None,
        instructions: str | None,
        tenant_id: str,
        db: AsyncSession,
    ) -> dict:
        # Load brand profile if specified
        brand_profile = None
        if brand_profile_id:
            result = await db.execute(
                select(BrandProfile).where(
                    BrandProfile.id == UUID(brand_profile_id),
                    BrandProfile.tenant_id == UUID(tenant_id),
                )
            )
            brand_profile = result.scalar_one_or_none()
        else:
            # Try to get default brand profile
            result = await db.execute(
                select(BrandProfile).where(
                    BrandProfile.tenant_id == UUID(tenant_id),
                    BrandProfile.is_default == True,
                )
            )
            brand_profile = result.scalar_one_or_none()

        # Build prompt using three-layer architecture
        system_prompt, user_prompt = self.prompt_builder.build(
            listing=listing,
            content_type=content_type,
            tone=tone,
            brand_profile=brand_profile,
            instructions=instructions,
        )

        # Select model
        model = MODEL_MAP.get(content_type, "claude-sonnet-4-5-20250929")

        # Circuit breaker check
        if not _circuit.allow_request():
            raise CircuitBreakerOpen()

        # Call Claude API with timeout and circuit breaker
        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            _circuit.record_success()
        except (anthropic.APIConnectionError, anthropic.APITimeoutError, httpx.TimeoutException) as exc:
            _circuit.record_failure()
            await logger.aerror("claude_api_error", error=str(exc), model=model, exc_info=True)
            raise
        except anthropic.APIStatusError as exc:
            # 5xx = transient, count toward circuit breaker; 4xx = caller error, don't
            if exc.status_code >= 500:
                _circuit.record_failure()
            await logger.aerror(
                "claude_api_status_error",
                status_code=exc.status_code,
                error=str(exc),
                model=model,
            )
            raise

        body = response.content[0].text
        metadata = self._extract_metadata(body, content_type)

        return {
            "body": body,
            "metadata": metadata,
            "model": model,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
        }

    def _extract_metadata(self, body: str, content_type: str) -> dict:
        metadata = {
            "word_count": len(body.split()),
            "character_count": len(body),
        }

        # Extract hashtags for social media content
        if content_type.startswith("social_"):
            hashtags = [word for word in body.split() if word.startswith("#")]
            metadata["hashtags"] = hashtags

        return metadata
