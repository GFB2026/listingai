"""Tests for MLS sync engine."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.mls.sync_engine import SyncEngine
from app.models.mls_connection import MLSConnection
from app.models.tenant import Tenant


def _make_connection(tenant_id, watermark=None) -> MLSConnection:
    conn = MLSConnection(
        tenant_id=tenant_id,
        provider="trestle",
        name="Test",
        base_url="https://api-trestle.corelogic.com",
        client_id_encrypted=b"enc_id",
        client_secret_encrypted=b"enc_secret",
        sync_enabled=True,
        sync_watermark=watermark,
    )
    return conn


def _reso_property(key="ABC123", mod_ts="2025-01-15T10:00:00Z"):
    return {
        "ListingKey": key,
        "ModificationTimestamp": mod_ts,
        "StreetNumber": "100",
        "StreetName": "Ocean",
        "StreetSuffix": "Blvd",
        "City": "Fort Lauderdale",
        "StateOrProvince": "FL",
        "PostalCode": "33308",
        "ListPrice": 500000,
        "BedroomsTotal": 3,
        "BathroomsTotalDecimal": 2,
        "LivingArea": 1800,
        "PropertyType": "Condominium",
        "StandardStatus": "Active",
    }


class TestSyncConnection:
    @pytest.mark.asyncio
    async def test_sync_empty_response(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        with patch(
            "app.integrations.mls.sync_engine.RESOClient.from_connection",
            return_value=mock_client,
        ):
            engine = SyncEngine(db_session)
            stats = await engine.sync_connection(conn)

        assert stats == {"created": 0, "updated": 0, "errors": 0, "total": 0}
        assert conn.last_sync_at is not None

    @pytest.mark.asyncio
    async def test_sync_with_records(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": [_reso_property()]})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_upsert = AsyncMock(return_value=(mock_listing, True))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["total"] == 1
        assert stats["created"] == 1
        mock_upsert.assert_called_once()
        # Watermark should advance on successful sync (zero errors)
        assert conn.sync_watermark == "2025-01-15T10:00:00Z"

    @pytest.mark.asyncio
    async def test_pagination(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        # First page: 200 records (full page), second page: 0 records
        page1 = [_reso_property(f"KEY{i}", "2025-01-15T10:00:00Z") for i in range(200)]
        page2 = []

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(side_effect=[{"value": page1}, {"value": page2}])
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        def _make_upsert_result(*args, **kwargs):
            mock_listing = MagicMock()
            mock_listing.id = uuid4()
            return (mock_listing, True)

        mock_upsert = AsyncMock(side_effect=_make_upsert_result)

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["total"] == 200
        assert mock_client.get_properties.call_count == 2

    @pytest.mark.asyncio
    async def test_watermark_filtering(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(test_tenant.id, watermark="2025-01-10T00:00:00Z")
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        with patch(
            "app.integrations.mls.sync_engine.RESOClient.from_connection",
            return_value=mock_client,
        ):
            engine = SyncEngine(db_session)
            await engine.sync_connection(conn)

        # Should have passed the watermark as a filter
        call_kwargs = mock_client.get_properties.call_args_list[0].kwargs
        assert "ModificationTimestamp gt" in (call_kwargs.get("filter_query") or "")

    @pytest.mark.asyncio
    async def test_record_level_error(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": [_reso_property()]})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_upsert = AsyncMock(side_effect=Exception("DB error"))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["errors"] == 1
        assert stats["total"] == 1

    @pytest.mark.asyncio
    async def test_watermark_not_advanced_on_errors(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """When a record fails processing, watermark should stay at original value."""
        original_watermark = "2025-01-10T00:00:00Z"
        conn = _make_connection(test_tenant.id, watermark=original_watermark)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": [_reso_property()]})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_upsert = AsyncMock(side_effect=Exception("DB error"))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["errors"] == 1
        # Watermark must NOT advance when there are errors
        assert conn.sync_watermark == original_watermark

    @pytest.mark.asyncio
    async def test_auto_gen_dispatched_for_new_listings(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": [_reso_property()]})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_upsert = AsyncMock(return_value=(mock_listing, True))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ) as mock_auto_gen,
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            await engine.sync_connection(conn)

        mock_auto_gen.delay.assert_called_once_with(
            tenant_id=str(conn.tenant_id),
            listing_ids=[str(mock_listing.id)],
        )

    @pytest.mark.asyncio
    async def test_auto_gen_not_dispatched_for_updates(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": [_reso_property()]})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_upsert = AsyncMock(return_value=(mock_listing, False))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ) as mock_auto_gen,
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            await engine.sync_connection(conn)

        mock_auto_gen.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_tenant(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_sync_connection = AsyncMock(
            return_value={"created": 1, "updated": 0, "errors": 0, "total": 1}
        )

        engine = SyncEngine(db_session)
        engine.sync_connection = mock_sync_connection
        results = await engine.sync_tenant(str(test_tenant.id))

        assert len(results) == 1
        assert results[0]["created"] == 1
        mock_sync_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_watermark_advances_to_latest_timestamp(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """When multiple records have different timestamps, watermark should be the latest."""
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        records = [
            _reso_property("A", "2025-01-10T08:00:00Z"),
            _reso_property("B", "2025-01-15T12:00:00Z"),
            _reso_property("C", "2025-01-12T06:00:00Z"),
        ]

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": records})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_upsert = AsyncMock(return_value=(mock_listing, True))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            await engine.sync_connection(conn)

        assert conn.sync_watermark == "2025-01-15T12:00:00Z"

    @pytest.mark.asyncio
    async def test_mixed_create_and_update_counts(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """Verify that create and update counts are tracked separately."""
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        records = [
            _reso_property("NEW1", "2025-01-15T10:00:00Z"),
            _reso_property("UPD1", "2025-01-15T10:01:00Z"),
            _reso_property("NEW2", "2025-01-15T10:02:00Z"),
        ]

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": records})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        call_count = 0

        async def _upsert_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_listing = MagicMock()
            mock_listing.id = uuid4()
            # 1st and 3rd are new, 2nd is an update
            return (mock_listing, call_count != 2)

        mock_upsert = AsyncMock(side_effect=_upsert_side_effect)

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["created"] == 2
        assert stats["updated"] == 1
        assert stats["total"] == 3
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_client_closed_on_fatal_error(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """RESOClient.close() must be called even if get_properties raises."""
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(side_effect=RuntimeError("API down"))
        mock_client.close = AsyncMock()

        with patch(
            "app.integrations.mls.sync_engine.RESOClient.from_connection",
            return_value=mock_client,
        ):
            engine = SyncEngine(db_session)
            with pytest.raises(RuntimeError, match="API down"):
                await engine.sync_connection(conn)

        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_media_error_does_not_crash_sync(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """If get_media raises for one record, it counts as an error but continues."""
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        records = [
            _reso_property("GOOD", "2025-01-15T10:00:00Z"),
            _reso_property("BAD_MEDIA", "2025-01-15T10:01:00Z"),
        ]

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": records})
        mock_client.close = AsyncMock()

        call_idx = 0

        async def _media_side_effect(key):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 2:
                raise ConnectionError("media fetch failed")
            return {"value": []}

        mock_client.get_media = AsyncMock(side_effect=_media_side_effect)

        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_upsert = AsyncMock(return_value=(mock_listing, True))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["total"] == 2
        assert stats["errors"] == 1
        assert stats["created"] == 1

    @pytest.mark.asyncio
    async def test_auto_gen_dispatch_failure_is_swallowed(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """If auto_generate dispatch fails, sync still completes successfully."""
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": [_reso_property()]})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_upsert = AsyncMock(return_value=(mock_listing, True))

        mock_auto_gen = MagicMock()
        mock_auto_gen.delay = MagicMock(side_effect=Exception("Celery down"))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
                mock_auto_gen,
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        # Sync should still report success; auto-gen failure is non-fatal
        assert stats["created"] == 1
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_sync_tenant_skips_disabled_connections(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """sync_tenant should only process connections with sync_enabled=True."""
        enabled = _make_connection(test_tenant.id)
        disabled = _make_connection(test_tenant.id)
        disabled.sync_enabled = False

        db_session.add_all([enabled, disabled])
        await db_session.flush()

        mock_sync_connection = AsyncMock(
            return_value={"created": 0, "updated": 0, "errors": 0, "total": 0}
        )

        engine = SyncEngine(db_session)
        engine.sync_connection = mock_sync_connection
        results = await engine.sync_tenant(str(test_tenant.id))

        assert len(results) == 1
        mock_sync_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_listing_key_skips_media_fetch(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        """If a record has no ListingKey, media fetch should be skipped."""
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        record = _reso_property()
        del record["ListingKey"]

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(return_value={"value": [record]})
        mock_client.get_media = AsyncMock(return_value={"value": []})
        mock_client.close = AsyncMock()

        mock_listing = MagicMock()
        mock_listing.id = uuid4()
        mock_upsert = AsyncMock(return_value=(mock_listing, True))

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch(
                "app.workers.tasks.content_auto_gen.auto_generate_for_new_listings",
            ),
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["total"] == 1
        assert stats["created"] == 1
        mock_client.get_media.assert_not_called()
