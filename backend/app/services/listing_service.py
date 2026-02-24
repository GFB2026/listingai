from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing


class ListingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_from_mls(
        self,
        tenant_id: UUID,
        mls_connection_id: UUID,
        mls_data: dict,
    ) -> tuple[Listing, bool]:
        """Insert or update a listing from normalized MLS data.

        Returns:
            Tuple of (listing, is_new) where is_new is True if the listing
            was created (not just updated).
        """
        mls_listing_id = mls_data.get("mls_listing_id")

        # Check for existing listing
        result = await self.db.execute(
            select(Listing).where(
                Listing.tenant_id == tenant_id,
                Listing.mls_listing_id == mls_listing_id,
            )
        )
        listing = result.scalar_one_or_none()

        if listing:
            # Update existing
            for key, value in mls_data.items():
                if hasattr(listing, key) and value is not None:
                    setattr(listing, key, value)
            is_new = False
        else:
            # Create new
            listing = Listing(
                tenant_id=tenant_id,
                mls_connection_id=mls_connection_id,
                **mls_data,
            )
            self.db.add(listing)
            is_new = True

        await self.db.flush()
        return listing, is_new
