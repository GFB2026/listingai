from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.api.deps import get_db
from app.core.database import Base, get_async_session
from app.core.security import hash_password
from app.main import create_app

# Import ALL models so Base.metadata knows about them for create_all/drop_all
from app.models.agent_page import AgentPage  # noqa: F401
from app.models.brand_profile import BrandProfile
from app.models.content import Content
from app.models.content_version import ContentVersion  # noqa: F401
from app.models.email_campaign import EmailCampaign  # noqa: F401
from app.models.lead import Lead  # noqa: F401
from app.models.lead_activity import LeadActivity  # noqa: F401
from app.models.listing import Listing
from app.models.mls_connection import MLSConnection  # noqa: F401
from app.models.page_visit import PageVisit  # noqa: F401
from app.models.social_post import SocialPost  # noqa: F401
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent  # noqa: F401
from app.models.user import User

settings = get_settings()

# Test database URL — only replace the database name (last path segment)
_base_url = settings.database_url
TEST_DATABASE_URL = _base_url.rsplit("/", 1)[0] + "/listingai_test"

_tables_created = False


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    global _tables_created
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    if not _tables_created:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    # Truncate all data between tests (fast, no DDL locks)
    async with engine.begin() as conn:
        table_names = ", ".join(
            f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
        )
        if table_names:
            await conn.execute(text(f"TRUNCATE {table_names} CASCADE"))

    await engine.dispose()


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        name="Test Brokerage",
        slug="test-brokerage",
        plan="professional",
        monthly_generation_limit=1000,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    user = User(
        tenant_id=test_tenant.id,
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        full_name="Test User",
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_session
    app.dependency_overrides[get_db] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Additional fixtures for integration tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_listing(db_session: AsyncSession, test_tenant: Tenant) -> Listing:
    """Pre-created listing for tests that need one."""
    listing = Listing(
        tenant_id=test_tenant.id,
        address_full="100 Ocean Blvd, Fort Lauderdale, FL 33308",
        address_street="100 Ocean Blvd",
        address_city="Fort Lauderdale",
        address_state="FL",
        address_zip="33308",
        price=1500000,
        bedrooms=3,
        bathrooms=2,
        sqft=2200,
        year_built=2015,
        property_type="condo",
        status="active",
        description_original="Beautiful oceanfront condo with panoramic views.",
        features=["Pool", "Ocean View", "Balcony"],
        photos=[{"url": "https://example.com/photo1.jpg"}],
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


@pytest_asyncio.fixture
async def test_brand_profile(db_session: AsyncSession, test_tenant: Tenant) -> BrandProfile:
    """Pre-created brand profile."""
    profile = BrandProfile(
        tenant_id=test_tenant.id,
        name="Luxury Coastal",
        is_default=True,
        voice_description="Professional and warm with emphasis on coastal living",
        vocabulary=["coastal", "premier", "sun-drenched"],
        avoid_words=["cheap", "fixer-upper"],
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


@pytest_asyncio.fixture
async def test_content(
    db_session: AsyncSession, test_tenant: Tenant, test_listing: Listing, test_user: User
) -> Content:
    """Pre-created content item."""
    content = Content(
        tenant_id=test_tenant.id,
        listing_id=test_listing.id,
        user_id=test_user.id,
        content_type="listing_description",
        tone="professional",
        body="A stunning oceanfront property with panoramic views...",
        content_metadata={"word_count": 50},
        ai_model="claude-sonnet-4-5-20250929",
        prompt_tokens=500,
        completion_tokens=200,
        generation_time_ms=2500,
    )
    db_session.add(content)
    await db_session.flush()
    return content


# --- Second tenant for isolation tests ---


@pytest_asyncio.fixture
async def other_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        name="Other Brokerage",
        slug="other-brokerage",
        plan="starter",
        monthly_generation_limit=200,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession, other_tenant: Tenant) -> User:
    user = User(
        tenant_id=other_tenant.id,
        email="other@example.com",
        password_hash=hash_password("Otherpassword1!"),
        full_name="Other User",
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    """Helper: login and return Authorization header dict."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    # Clear cookies so CSRF middleware doesn't trigger on Bearer-auth requests
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}
