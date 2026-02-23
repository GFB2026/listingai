"""Tests for MLS sync engine."""
from unittest.mock import AsyncMock, MagicMock, patch

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

        mock_upsert = AsyncMock(return_value=MagicMock())

        with (
            patch(
                "app.integrations.mls.sync_engine.RESOClient.from_connection",
                return_value=mock_client,
            ),
            patch.object(
                SyncEngine, "__init__", lambda self, db: setattr(self, "db", db) or setattr(self, "listing_service", MagicMock(upsert_from_mls=mock_upsert)),
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

        mock_upsert = AsyncMock(return_value=MagicMock())

        with patch(
            "app.integrations.mls.sync_engine.RESOClient.from_connection",
            return_value=mock_client,
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

        with patch(
            "app.integrations.mls.sync_engine.RESOClient.from_connection",
            return_value=mock_client,
        ):
            engine = SyncEngine.__new__(SyncEngine)
            engine.db = db_session
            engine.listing_service = MagicMock(upsert_from_mls=mock_upsert)
            stats = await engine.sync_connection(conn)

        assert stats["errors"] == 1
        assert stats["total"] == 1

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
