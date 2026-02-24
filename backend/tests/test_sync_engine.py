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
        mock_client.get_properties = AsyncMock(
            return_value={"value": [_reso_property()]}
        )
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

    @pytest.mark.asyncio
    async def test_pagination(self, db_session: AsyncSession, test_tenant: Tenant):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        # First page: 200 records (full page), second page: 0 records
        page1 = [_reso_property(f"KEY{i}", "2025-01-15T10:00:00Z") for i in range(200)]
        page2 = []

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(
            side_effect=[{"value": page1}, {"value": page2}]
        )
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
        mock_client.get_properties = AsyncMock(
            return_value={"value": [_reso_property()]}
        )
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
    async def test_auto_gen_dispatched_for_new_listings(
        self, db_session: AsyncSession, test_tenant: Tenant
    ):
        conn = _make_connection(test_tenant.id)
        db_session.add(conn)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_client.get_properties = AsyncMock(
            return_value={"value": [_reso_property()]}
        )
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
        mock_client.get_properties = AsyncMock(
            return_value={"value": [_reso_property()]}
        )
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
