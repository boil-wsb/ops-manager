"""
Pytest configuration and fixtures.
"""
import asyncio
import os

os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.base_class import Base
from app.config import settings
from app.core.rate_limit import limiter


TEST_DATABASE_URL = os.environ.get("DATABASE_URL", settings.async_database_url)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_and_teardown_db():
    """Run Alembic migrations to ensure schema is up to date, then create any missing tables."""
    from alembic.config import Config as AlembicConfig
    from alembic import command

    alembic_cfg = AlembicConfig("alembic.ini")
    database_url = TEST_DATABASE_URL
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="session", autouse=True)
def create_test_users():
    """Create test users for authentication tests.

    Note: Admin account (admin/admin123) is assumed to exist in the database.
    This fixture does not create or modify the admin user.
    Other test users can be dynamically generated in individual tests.
    """
    yield


@pytest.fixture(scope="function", autouse=True)
def reset_rate_limiter():
    """Reset rate limiter storage before each test."""
    if settings.disable_rate_limit:
        limiter._storage.reset()
    yield


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests with transaction rollback."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def anyio_backend():
    return "asyncio"
