import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.mls.adapters import MediaAdapter, PropertyAdapter
from app.integrations.mls.reso_client import RESOClient
from app.models.mls_connection import MLSConnection
from app.services.listing_service import ListingService

logger = structlog.get_logger()


class SyncEngine:
    """Incremental MLS sync using ModificationTimestamp watermark."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.listing_service = ListingService(db)

    async def sync_connection(self, connection: MLSConnection) -> dict:
        """Run incremental sync for a single MLS connection."""
        client = RESOClient.from_connection(connection)
        stats = {"created": 0, "updated": 0, "errors": 0, "total": 0}

        try:
            # Build filter using watermark for incremental sync
            filter_query = None
            if connection.sync_watermark:
                filter_query = (
                    f"ModificationTimestamp gt {connection.sync_watermark}"
                )

            latest_timestamp = connection.sync_watermark
            skip = 0
            page_size = 200

            while True:
                data = await client.get_properties(
                    filter_query=filter_query,
                    top=page_size,
                    skip=skip,
                )

                records = data.get("value", [])
                if not records:
                    break

                for record in records:
                    stats["total"] += 1
                    try:
                        normalized = PropertyAdapter.normalize(record)

                        # Sync photos
                        listing_key = record.get("ListingKey")
                        if listing_key:
                            media_data = await client.get_media(listing_key)
                            photos = [
                                MediaAdapter.normalize(m)
                                for m in media_data.get("value", [])
                            ]
                            normalized["photos"] = photos

                        await self.listing_service.upsert_from_mls(
                            tenant_id=connection.tenant_id,
                            mls_connection_id=connection.id,
                            mls_data=normalized,
                        )

                        # Track latest timestamp
                        mod_ts = record.get("ModificationTimestamp")
                        if mod_ts and (not latest_timestamp or mod_ts > latest_timestamp):
                            latest_timestamp = mod_ts

                        stats["created" if not normalized.get("id") else "updated"] += 1

                    except Exception as e:
                        stats["errors"] += 1
                        await logger.aerror(
                            "sync_record_error",
                            listing_key=record.get("ListingKey"),
                            error=str(e),
                        )

                skip += page_size

                # Check if we got fewer records than page size (last page)
                if len(records) < page_size:
                    break

            # Update watermark
            if latest_timestamp:
                connection.sync_watermark = latest_timestamp
            connection.last_sync_at = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            self.db.add(connection)

        finally:
            await client.close()

        await logger.ainfo("sync_complete", connection_id=str(connection.id), stats=stats)
        return stats

    async def sync_tenant(self, tenant_id: str) -> list[dict]:
        """Sync all enabled MLS connections for a tenant."""
        from uuid import UUID

        result = await self.db.execute(
            select(MLSConnection).where(
                MLSConnection.tenant_id == UUID(tenant_id),
                MLSConnection.sync_enabled == True,
            )
        )
        connections = result.scalars().all()

        results = []
        for connection in connections:
            stats = await self.sync_connection(connection)
            results.append({"connection_id": str(connection.id), **stats})

        return results
