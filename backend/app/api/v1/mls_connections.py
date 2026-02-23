from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_db
from app.core.encryption import decrypt_value, encrypt_value
from app.integrations.mls.reso_client import RESOClient
from app.models.listing import Listing
from app.models.mls_connection import MLSConnection
from app.models.user import User
from app.schemas.mls_connection import (
    MLSConnectionCreate,
    MLSConnectionListResponse,
    MLSConnectionResponse,
    MLSConnectionStatus,
    MLSConnectionTestResult,
    MLSConnectionUpdate,
)

router = APIRouter()


@router.get("", response_model=MLSConnectionListResponse)
async def list_connections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all MLS connections for the current tenant."""
    result = await db.execute(
        select(MLSConnection).where(
            MLSConnection.tenant_id == user.tenant_id
        ).order_by(MLSConnection.created_at.desc())
    )
    connections = result.scalars().all()
    return MLSConnectionListResponse(
        connections=[MLSConnectionResponse.model_validate(c) for c in connections]
    )


@router.post("", response_model=MLSConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    request: MLSConnectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a new MLS connection with encrypted credentials."""
    connection = MLSConnection(
        tenant_id=user.tenant_id,
        provider=request.provider,
        name=request.name,
        base_url=request.base_url,
        client_id_encrypted=encrypt_value(request.client_id),
        client_secret_encrypted=encrypt_value(request.client_secret),
        sync_enabled=request.sync_enabled,
    )
    db.add(connection)
    await db.flush()
    return MLSConnectionResponse.model_validate(connection)


@router.patch("/{connection_id}", response_model=MLSConnectionResponse)
async def update_connection(
    connection_id: str,
    request: MLSConnectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Update an existing MLS connection."""
    result = await db.execute(
        select(MLSConnection).where(
            MLSConnection.id == UUID(connection_id),
            MLSConnection.tenant_id == user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="MLS connection not found")

    if request.name is not None:
        connection.name = request.name
    if request.base_url is not None:
        connection.base_url = request.base_url
    if request.client_id is not None:
        connection.client_id_encrypted = encrypt_value(request.client_id)
    if request.client_secret is not None:
        connection.client_secret_encrypted = encrypt_value(request.client_secret)
    if request.sync_enabled is not None:
        connection.sync_enabled = request.sync_enabled

    db.add(connection)
    await db.flush()
    return MLSConnectionResponse.model_validate(connection)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Delete an MLS connection."""
    result = await db.execute(
        select(MLSConnection).where(
            MLSConnection.id == UUID(connection_id),
            MLSConnection.tenant_id == user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="MLS connection not found")

    await db.delete(connection)
    await db.flush()


@router.post("/{connection_id}/test", response_model=MLSConnectionTestResult)
async def test_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Test an MLS connection by authenticating and fetching one property."""
    result = await db.execute(
        select(MLSConnection).where(
            MLSConnection.id == UUID(connection_id),
            MLSConnection.tenant_id == user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="MLS connection not found")

    client = RESOClient.from_connection(connection)
    try:
        await client.authenticate()
        data = await client.get_properties(top=1)
        count = len(data.get("value", []))
        return MLSConnectionTestResult(
            success=True,
            message="Successfully connected and retrieved data",
            property_count=count,
        )
    except Exception as e:
        return MLSConnectionTestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
        )
    finally:
        await client.close()


@router.get("/{connection_id}/status", response_model=MLSConnectionStatus)
async def get_connection_status(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get sync status for an MLS connection."""
    result = await db.execute(
        select(MLSConnection).where(
            MLSConnection.id == UUID(connection_id),
            MLSConnection.tenant_id == user.tenant_id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="MLS connection not found")

    # Count listings for this connection (tenant-scoped)
    count_result = await db.execute(
        select(func.count()).select_from(Listing).where(
            Listing.mls_connection_id == connection.id,
            Listing.tenant_id == user.tenant_id,
        )
    )
    listing_count = count_result.scalar() or 0

    return MLSConnectionStatus(
        id=str(connection.id),
        name=connection.name,
        sync_enabled=connection.sync_enabled,
        last_sync_at=connection.last_sync_at,
        sync_watermark=connection.sync_watermark,
        listing_count=listing_count,
    )
