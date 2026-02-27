"""Tests for Celery worker tasks (async helpers + Celery wrappers)."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from celery.exceptions import SoftTimeLimitExceeded


class TestSyncTenantHelper:
    @pytest.mark.asyncio
    async def test_sync_tenant(self):
        from app.workers.tasks.mls_sync import _sync_tenant

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_engine = MagicMock()
        mock_engine.sync_tenant = AsyncMock(
            return_value=[{
                "connection_id": "c1",
                "created": 5,
                "updated": 0,
                "errors": 0,
                "total": 5,
            }]
        )

        tenant_id = str(uuid4())

        # Local imports in _sync_tenant — patch at source modules
        with (
            patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ),
            patch(
                "app.integrations.mls.sync_engine.SyncEngine",
                return_value=mock_engine,
            ),
        ):
            await _sync_tenant(tenant_id)

        mock_engine.sync_tenant.assert_called_once_with(tenant_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_all(self):
        from app.workers.tasks.mls_sync import _sync_all

        tenant_id = str(uuid4())

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.all.return_value = [(tenant_id,)]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_engine = MagicMock()
        mock_engine.sync_tenant = AsyncMock(return_value=[])

        with (
            patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ),
            patch(
                "app.integrations.mls.sync_engine.SyncEngine",
                return_value=mock_engine,
            ),
        ):
            await _sync_all()

    @pytest.mark.asyncio
    async def test_sync_all_tenant_error(self):
        """One tenant failing doesn't crash the whole loop."""
        from app.workers.tasks.mls_sync import _sync_all

        t1, t2 = str(uuid4()), str(uuid4())

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.all.return_value = [(t1,), (t2,)]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # Patch _sync_tenant itself for this test
        with patch(
            "app.workers.tasks.mls_sync._sync_tenant",
            side_effect=[Exception("boom"), None],
        ):
            with patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ):
                # Should not raise — errors are caught
                await _sync_all()


class TestSyncMlsListingsCeleryTask:
    def test_celery_task_calls_asyncio_run(self):
        from app.workers.tasks.mls_sync import sync_mls_listings

        tenant_id = str(uuid4())
        with patch("app.workers.tasks.mls_sync.asyncio.run") as mock_run:
            sync_mls_listings(tenant_id=tenant_id, correlation_id=None)
            mock_run.assert_called_once()

    def test_celery_task_retries_on_error(self):
        from app.workers.tasks.mls_sync import sync_mls_listings

        tenant_id = str(uuid4())
        with patch(
            "app.workers.tasks.mls_sync.asyncio.run",
            side_effect=Exception("fail"),
        ):
            with pytest.raises(Exception):
                sync_mls_listings(tenant_id=tenant_id, correlation_id=None)

    def test_celery_task_with_correlation_id(self):
        from app.workers.tasks.mls_sync import sync_mls_listings

        tenant_id = str(uuid4())
        with (
            patch("app.workers.tasks.mls_sync.asyncio.run") as mock_run,
            patch("app.workers.tasks.mls_sync.structlog.contextvars.bind_contextvars") as mock_bind,
        ):
            sync_mls_listings(tenant_id=tenant_id, correlation_id="req-123")
            mock_bind.assert_called_once_with(correlation_id="req-123")
            mock_run.assert_called_once()

    def test_celery_task_soft_time_limit(self):
        from app.workers.tasks.mls_sync import sync_mls_listings

        tenant_id = str(uuid4())
        with patch(
            "app.workers.tasks.mls_sync.asyncio.run",
            side_effect=SoftTimeLimitExceeded(),
        ):
            with pytest.raises(SoftTimeLimitExceeded):
                sync_mls_listings(tenant_id=tenant_id, correlation_id=None)


class TestSyncAllTenantsCeleryTask:
    def test_calls_asyncio_run(self):
        from app.workers.tasks.mls_sync import sync_all_tenants

        with patch("app.workers.tasks.mls_sync.asyncio.run") as mock_run:
            sync_all_tenants(correlation_id=None)
            mock_run.assert_called_once()

    def test_with_correlation_id(self):
        from app.workers.tasks.mls_sync import sync_all_tenants

        with (
            patch("app.workers.tasks.mls_sync.asyncio.run"),
            patch("app.workers.tasks.mls_sync.structlog.contextvars.bind_contextvars") as mock_bind,
        ):
            sync_all_tenants(correlation_id="req-456")
            mock_bind.assert_called_once_with(correlation_id="req-456")

    def test_soft_time_limit(self):
        from app.workers.tasks.mls_sync import sync_all_tenants

        with patch(
            "app.workers.tasks.mls_sync.asyncio.run",
            side_effect=SoftTimeLimitExceeded(),
        ):
            with pytest.raises(SoftTimeLimitExceeded):
                sync_all_tenants(correlation_id=None)

    def test_retries_on_error(self):
        from app.workers.tasks.mls_sync import sync_all_tenants

        with patch(
            "app.workers.tasks.mls_sync.asyncio.run",
            side_effect=Exception("boom"),
        ):
            with pytest.raises(Exception):
                sync_all_tenants(correlation_id=None)


class TestBatchGenerateCeleryTask:
    def test_calls_asyncio_run(self):
        from app.workers.tasks.content_batch import batch_generate_content

        with patch("app.workers.tasks.content_batch.asyncio.run") as mock_run:
            batch_generate_content(
                tenant_id="t1", user_id="u1", listing_ids=["l1"],
                content_type="listing_description", correlation_id=None,
            )
            mock_run.assert_called_once()

    def test_with_correlation_id(self):
        from app.workers.tasks.content_batch import batch_generate_content

        with (
            patch("app.workers.tasks.content_batch.asyncio.run"),
            patch(
                "app.workers.tasks.content_batch"
                ".structlog.contextvars.bind_contextvars",
            ) as mock_bind,
        ):
            batch_generate_content(
                tenant_id="t1", user_id="u1", listing_ids=["l1"],
                content_type="listing_description", correlation_id="req-789",
            )
            mock_bind.assert_called_once_with(correlation_id="req-789")

    def test_soft_time_limit(self):
        from app.workers.tasks.content_batch import batch_generate_content

        with patch(
            "app.workers.tasks.content_batch.asyncio.run",
            side_effect=SoftTimeLimitExceeded(),
        ):
            with pytest.raises(SoftTimeLimitExceeded):
                batch_generate_content(
                    tenant_id="t1", user_id="u1", listing_ids=["l1"],
                    content_type="listing_description", correlation_id=None,
                )

    def test_retries_on_error(self):
        from app.workers.tasks.content_batch import batch_generate_content

        with patch(
            "app.workers.tasks.content_batch.asyncio.run",
            side_effect=Exception("fail"),
        ):
            with pytest.raises(Exception):
                batch_generate_content(
                    tenant_id="t1", user_id="u1", listing_ids=["l1"],
                    content_type="listing_description", correlation_id=None,
                )


class TestBatchGenerateHelper:
    @pytest.mark.asyncio
    async def test_batch_generate(self):
        from app.workers.tasks.content_batch import _batch_generate

        tenant_id = str(uuid4())
        user_id = str(uuid4())
        listing_id = str(uuid4())

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_listing = MagicMock()
        mock_listing.id = listing_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(
            return_value={
                "body": "Generated content",
                "model": "claude-sonnet-4-5-20250929",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "metadata": {"word_count": 2},
            }
        )

        mock_content_service = MagicMock()
        mock_content_service.create = AsyncMock(return_value=MagicMock())

        # Local imports in _batch_generate — patch at source modules
        with (
            patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ),
            patch("app.middleware.tenant_context.set_tenant_context", new_callable=AsyncMock),
            patch("app.services.ai_service.AIService", return_value=mock_ai),
            patch(
                "app.services.content_service.ContentService",
                return_value=mock_content_service,
            ),
        ):
            await _batch_generate(
                tenant_id=tenant_id,
                user_id=user_id,
                listing_ids=[listing_id],
                content_type="listing_description",
                tone="professional",
                brand_profile_id=None,
            )

        mock_ai.generate.assert_called_once()
        mock_content_service.create.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_generate_item_error(self):
        """Per-listing errors don't stop the batch."""
        from app.workers.tasks.content_batch import _batch_generate

        tenant_id = str(uuid4())
        user_id = str(uuid4())
        lid1, lid2 = str(uuid4()), str(uuid4())

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_listing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(
            side_effect=[Exception("AI failed"), AsyncMock(return_value={
                "body": "OK",
                "model": "claude-sonnet-4-5-20250929",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "metadata": {},
            })]
        )

        mock_content_service = MagicMock()
        mock_content_service.create = AsyncMock(return_value=MagicMock())

        with (
            patch(
                "app.core.database.async_session_factory",
                return_value=mock_session,
            ),
            patch("app.middleware.tenant_context.set_tenant_context", new_callable=AsyncMock),
            patch("app.services.ai_service.AIService", return_value=mock_ai),
            patch(
                "app.services.content_service.ContentService",
                return_value=mock_content_service,
            ),
        ):
            # Should not raise
            await _batch_generate(
                tenant_id=tenant_id,
                user_id=user_id,
                listing_ids=[lid1, lid2],
                content_type="listing_description",
                tone="professional",
                brand_profile_id=None,
            )

        # Commit should still be called
        mock_session.commit.assert_called_once()


class TestBatchGenerateListingNotFound:
    @pytest.mark.asyncio
    async def test_listing_not_found_skips(self):
        """When a listing is not found, it's skipped (no error raised)."""
        from app.workers.tasks.content_batch import _batch_generate

        tenant_id = str(uuid4())
        user_id = str(uuid4())

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # listing not found
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock()

        with (
            patch("app.core.database.async_session_factory", return_value=mock_session),
            patch("app.middleware.tenant_context.set_tenant_context", new_callable=AsyncMock),
            patch("app.services.ai_service.AIService", return_value=mock_ai),
            patch("app.services.content_service.ContentService"),
        ):
            await _batch_generate(
                tenant_id=tenant_id, user_id=user_id,
                listing_ids=[str(uuid4())],
                content_type="listing_description", tone="professional",
                brand_profile_id=None,
            )

        # AI should not have been called since listing was not found
        mock_ai.generate.assert_not_called()
        mock_session.commit.assert_called_once()


class TestDownloadListingPhotosCeleryTask:
    def test_calls_asyncio_run(self):
        from app.workers.tasks.media_process import download_listing_photos

        with patch("app.workers.tasks.media_process.asyncio.run") as mock_run:
            download_listing_photos(
                tenant_id="t1", listing_id="l1", photo_urls=[], correlation_id=None,
            )
            mock_run.assert_called_once()

    def test_with_correlation_id(self):
        from app.workers.tasks.media_process import download_listing_photos

        with (
            patch("app.workers.tasks.media_process.asyncio.run"),
            patch(
                "app.workers.tasks.media_process"
                ".structlog.contextvars.bind_contextvars",
            ) as mock_bind,
        ):
            download_listing_photos(
                tenant_id="t1", listing_id="l1", photo_urls=[], correlation_id="req-abc",
            )
            mock_bind.assert_called_once_with(correlation_id="req-abc")

    def test_soft_time_limit(self):
        from app.workers.tasks.media_process import download_listing_photos

        with patch(
            "app.workers.tasks.media_process.asyncio.run",
            side_effect=SoftTimeLimitExceeded(),
        ):
            with pytest.raises(SoftTimeLimitExceeded):
                download_listing_photos(
                    tenant_id="t1", listing_id="l1", photo_urls=[], correlation_id=None,
                )

    def test_retries_on_error(self):
        from app.workers.tasks.media_process import download_listing_photos

        with patch(
            "app.workers.tasks.media_process.asyncio.run",
            side_effect=Exception("fail"),
        ):
            with pytest.raises(Exception):
                download_listing_photos(
                    tenant_id="t1", listing_id="l1", photo_urls=[], correlation_id=None,
                )


class TestDownloadPhotosErrorHandling:
    @pytest.mark.asyncio
    async def test_download_error_continues(self):
        """Per-photo errors don't stop the batch."""
        from app.workers.tasks.media_process import _download_photos

        mock_media = MagicMock()
        mock_media.download_from_url = AsyncMock(
            side_effect=[
                Exception("network error"),
                {"media_id": "m2", "key": "path/2.jpg"},
            ]
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_listing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.media_service.MediaService", return_value=mock_media),
            patch(
                "app.workers.tasks.media_process"
                ".async_session_factory",
                return_value=mock_session,
            ),
            patch(
                "app.workers.tasks.media_process"
                ".set_tenant_context",
                new_callable=AsyncMock,
            ),
        ):
            await _download_photos(
                str(uuid4()), str(uuid4()),
                [
                    {"url": "https://example.com/1.jpg", "order": 0},
                    {"url": "https://example.com/2.jpg", "order": 1},
                ],
            )

        # Only the second photo should be stored
        assert mock_listing.photos == [{"media_id": "m2", "key": "path/2.jpg"}]


class TestDownloadPhotosHelper:
    @pytest.mark.asyncio
    async def test_download_photos(self):
        from app.workers.tasks.media_process import _download_photos

        tenant_id = str(uuid4())
        listing_id = str(uuid4())

        mock_media = MagicMock()
        mock_media.download_from_url = AsyncMock(
            return_value={"media_id": "m1", "key": "path/photo.jpg"}
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_listing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_listing
        mock_session.execute = AsyncMock(return_value=mock_result)

        # MediaService is local import in _download_photos
        with (
            patch(
                "app.services.media_service.MediaService",
                return_value=mock_media,
            ),
            patch(
                "app.workers.tasks.media_process.async_session_factory",
                return_value=mock_session,
            ),
            patch(
                "app.workers.tasks.media_process.set_tenant_context",
                new_callable=AsyncMock,
            ),
        ):
            await _download_photos(
                tenant_id, listing_id, [{"url": "https://example.com/photo.jpg", "order": 0}]
            )

        mock_media.download_from_url.assert_called_once()
        assert mock_listing.photos == [{"media_id": "m1", "key": "path/photo.jpg"}]

    @pytest.mark.asyncio
    async def test_download_empty_urls(self):
        from app.workers.tasks.media_process import _download_photos

        mock_media = MagicMock()
        mock_media.download_from_url = AsyncMock()

        with patch(
            "app.services.media_service.MediaService",
            return_value=mock_media,
        ):
            await _download_photos(str(uuid4()), str(uuid4()), [])

        mock_media.download_from_url.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_skips_missing_url(self):
        from app.workers.tasks.media_process import _download_photos

        mock_media = MagicMock()
        mock_media.download_from_url = AsyncMock()

        with patch(
            "app.services.media_service.MediaService",
            return_value=mock_media,
        ):
            await _download_photos(
                str(uuid4()), str(uuid4()), [{"order": 0}]  # no "url" key
            )

        mock_media.download_from_url.assert_not_called()
