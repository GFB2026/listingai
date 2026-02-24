"""Tests for content_auto_gen Celery task — auto-generates content for new listings."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from celery.exceptions import SoftTimeLimitExceeded


# ── Celery wrapper tests ─────────────────────────────────────────


class TestAutoGenerateTask:
    def test_runs_asyncio(self):
        """Task calls asyncio.run(_auto_generate(...))."""
        from app.workers.tasks.content_auto_gen import auto_generate_for_new_listings

        tid = str(uuid4())
        lids = [str(uuid4())]

        with patch(
            "app.workers.tasks.content_auto_gen.asyncio.run",
        ) as mock_run:
            auto_generate_for_new_listings(tid, lids)

        mock_run.assert_called_once()

    def test_binds_correlation_id(self):
        """When correlation_id is set, structlog contextvars are bound."""
        from app.workers.tasks.content_auto_gen import auto_generate_for_new_listings

        tid = str(uuid4())

        with (
            patch("app.workers.tasks.content_auto_gen.asyncio.run"),
            patch(
                "app.workers.tasks.content_auto_gen.structlog.contextvars.bind_contextvars"
            ) as mock_bind,
        ):
            auto_generate_for_new_listings(tid, [], correlation_id="req-abc")

        mock_bind.assert_called_once_with(correlation_id="req-abc")

    def test_no_correlation_id(self):
        """Without correlation_id, contextvars are not bound."""
        from app.workers.tasks.content_auto_gen import auto_generate_for_new_listings

        with (
            patch("app.workers.tasks.content_auto_gen.asyncio.run"),
            patch(
                "app.workers.tasks.content_auto_gen.structlog.contextvars.bind_contextvars"
            ) as mock_bind,
        ):
            auto_generate_for_new_listings(str(uuid4()), [])

        mock_bind.assert_not_called()

    def test_soft_time_limit(self):
        """SoftTimeLimitExceeded is logged and re-raised."""
        from app.workers.tasks.content_auto_gen import auto_generate_for_new_listings

        with (
            patch(
                "app.workers.tasks.content_auto_gen.asyncio.run",
                side_effect=SoftTimeLimitExceeded(),
            ),
            pytest.raises(SoftTimeLimitExceeded),
        ):
            auto_generate_for_new_listings(str(uuid4()), [str(uuid4())])

    def test_general_exception_retries(self):
        """General exceptions trigger self.retry()."""
        from app.workers.tasks.content_auto_gen import auto_generate_for_new_listings

        exc = RuntimeError("boom")
        with (
            patch(
                "app.workers.tasks.content_auto_gen.asyncio.run",
                side_effect=exc,
            ),
            patch.object(
                auto_generate_for_new_listings,
                "retry",
                side_effect=RuntimeError("retried"),
            ) as mock_retry,
            pytest.raises(RuntimeError, match="retried"),
        ):
            auto_generate_for_new_listings(str(uuid4()), [str(uuid4())])

        mock_retry.assert_called_once()


# ── Async helper tests ───────────────────────────────────────────


class TestAutoGenerateHelper:
    @pytest.mark.asyncio
    async def test_tenant_not_found(self):
        """Returns early when tenant doesn't exist."""
        from app.workers.tasks.content_auto_gen import _auto_generate

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Tenant query returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        tid = str(uuid4())
        with patch(
            "app.core.database.async_session_factory",
            return_value=mock_session,
        ):
            await _auto_generate(tid, [str(uuid4())])

        # Should NOT commit — early return
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_gen_disabled(self):
        """Returns early when tenant settings disable auto-gen."""
        from app.workers.tasks.content_auto_gen import _auto_generate

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {"auto_generate_on_new_listing": False}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.database.async_session_factory",
            return_value=mock_session,
        ):
            await _auto_generate(str(mock_tenant.id), [str(uuid4())])

        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_system_user(self):
        """Returns early when no admin/owner user exists."""
        from app.workers.tasks.content_auto_gen import _auto_generate

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {}

        # First call: tenant, second: brand profile, third: system user
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # set_tenant_context
                return result
            if call_count == 2:
                # tenant
                result.scalar_one_or_none.return_value = mock_tenant
            elif call_count == 3:
                # brand profile
                result.scalar_one_or_none.return_value = None
            elif call_count == 4:
                # system user
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        with patch(
            "app.core.database.async_session_factory",
            return_value=mock_session,
        ):
            await _auto_generate(str(mock_tenant.id), [str(uuid4())])

        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_listing_not_found_skipped(self):
        """Missing listing is skipped but processing continues."""
        from app.workers.tasks.content_auto_gen import _auto_generate

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        tenant_id = uuid4()
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.settings = {}

        mock_user = MagicMock()
        mock_user.id = uuid4()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                return result  # set_tenant_context
            if call_count == 2:
                result.scalar_one_or_none.return_value = mock_tenant
            elif call_count == 3:
                result.scalar_one_or_none.return_value = None  # no brand profile
            elif call_count == 4:
                result.scalar_one_or_none.return_value = mock_user
            elif call_count >= 5:
                result.scalar_one_or_none.return_value = None  # listing not found
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        with patch(
            "app.core.database.async_session_factory",
            return_value=mock_session,
        ):
            await _auto_generate(str(tenant_id), [str(uuid4())])

        # Should still commit even with no listings found
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_generation(self):
        """Successful generation creates content for each listing x content_type."""
        from app.workers.tasks.content_auto_gen import _auto_generate

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        tenant_id = uuid4()
        listing_id = uuid4()
        user_id = uuid4()
        bp_id = uuid4()

        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        # Only generate one content type for speed
        mock_tenant.settings = {"auto_generate_content_types": ["listing_description"]}

        mock_bp = MagicMock()
        mock_bp.id = bp_id

        mock_user = MagicMock()
        mock_user.id = user_id

        mock_listing = MagicMock()
        mock_listing.id = listing_id

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                return result  # set_tenant_context
            if call_count == 2:
                result.scalar_one_or_none.return_value = mock_tenant
            elif call_count == 3:
                result.scalar_one_or_none.return_value = mock_bp
            elif call_count == 4:
                result.scalar_one_or_none.return_value = mock_user
            elif call_count == 5:
                result.scalar_one_or_none.return_value = mock_listing
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(return_value={
            "body": "Beautiful property...",
            "model": "claude-sonnet-4-5-20250929",
            "metadata": {},
            "prompt_tokens": 100,
            "completion_tokens": 200,
        })

        mock_content_service = MagicMock()
        mock_content_service.create = AsyncMock()

        with (
            patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ),
            patch(
                "app.services.ai_service.AIService",
                return_value=mock_ai,
            ),
            patch(
                "app.services.content_service.ContentService",
                return_value=mock_content_service,
            ),
        ):
            await _auto_generate(str(tenant_id), [str(listing_id)])

        mock_ai.generate.assert_called_once()
        mock_content_service.create.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generation_error_counted(self):
        """An error during AI generation increments error count but continues."""
        from app.workers.tasks.content_auto_gen import _auto_generate

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        tenant_id = uuid4()
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.settings = {"auto_generate_content_types": ["listing_description"]}

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                return result  # set_tenant_context
            if call_count == 2:
                result.scalar_one_or_none.return_value = mock_tenant
            elif call_count == 3:
                result.scalar_one_or_none.return_value = None  # no brand profile
            elif call_count == 4:
                result.scalar_one_or_none.return_value = mock_user
            elif call_count == 5:
                result.scalar_one_or_none.return_value = mock_listing
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(side_effect=RuntimeError("AI down"))

        with (
            patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ),
            patch(
                "app.services.ai_service.AIService",
                return_value=mock_ai,
            ),
        ):
            # Should not raise — errors are caught and counted
            await _auto_generate(str(tenant_id), [str(uuid4())])

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_tone_from_settings(self):
        """Tenant settings override default tone."""
        from app.workers.tasks.content_auto_gen import _auto_generate

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        tenant_id = uuid4()
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.settings = {
            "auto_generate_content_types": ["social_x"],
            "auto_generate_tone": "luxury",
        }

        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                return result
            if call_count == 2:
                result.scalar_one_or_none.return_value = mock_tenant
            elif call_count == 3:
                result.scalar_one_or_none.return_value = None
            elif call_count == 4:
                result.scalar_one_or_none.return_value = mock_user
            elif call_count == 5:
                result.scalar_one_or_none.return_value = mock_listing
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(return_value={
            "body": "Luxury tweet",
            "model": "claude-haiku-4-5-20251001",
            "prompt_tokens": 50,
            "completion_tokens": 30,
        })

        mock_content_service = MagicMock()
        mock_content_service.create = AsyncMock()

        with (
            patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ),
            patch(
                "app.services.ai_service.AIService",
                return_value=mock_ai,
            ),
            patch(
                "app.services.content_service.ContentService",
                return_value=mock_content_service,
            ),
        ):
            await _auto_generate(str(tenant_id), [str(uuid4())])

        # Verify tone was passed through
        call_kwargs = mock_ai.generate.call_args
        assert call_kwargs.kwargs["tone"] == "luxury"
