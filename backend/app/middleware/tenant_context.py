from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """Set the PostgreSQL session variable for Row-Level Security."""
    await session.execute(
        text("SET app.current_tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_id)},
    )
