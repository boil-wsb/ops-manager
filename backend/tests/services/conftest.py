"""
Services layer conftest.

Override parent setup_and_teardown_db to skip DB schema initialization.
Reason: pytest-cov's trace function conflicts with asyncpg's SSL connection
on Windows, causing access violation during Base.metadata.create_all().

- L2/L3 unit tests are pure Mock and don't need real DB.
- L5/L6 integration tests use db_operation_with_retry to create independent
  sessions against the existing schema (already created by alembic migrations
  in prior test runs).
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
async def setup_and_teardown_db():
    """Skip DB schema initialization to avoid asyncpg SSL access violation
    under pytest-cov trace on Windows.

    Schema is assumed to already exist via alembic migrations.
    """
    yield
