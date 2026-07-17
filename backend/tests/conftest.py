"""
Pytest configuration and fixtures.
"""
import asyncio
import os

os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.rate_limit import limiter
from app.db.base_class import Base
from app.main import app

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
    import subprocess
    import sys

    database_url = TEST_DATABASE_URL
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    env = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "DATABASE_URL": database_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        check=False,
    )

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
