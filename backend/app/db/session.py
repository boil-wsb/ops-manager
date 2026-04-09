"""
Database session management.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


@lru_cache
def get_engine():
    """Get or create the async engine (lazy initialization)."""
    return create_async_engine(
        settings.async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        echo=False,
    )


@lru_cache
def get_session_maker():
    """Get or create the async session maker (lazy initialization)."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_db() -> AsyncSession:
    """Get a database session (for FastAPI dependency injection)."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_session():
    """Get a database session (for use with async with)."""
    session_maker = get_session_maker()
    return session_maker()


async def get_async_session_local():
    """Get a new async session local for direct use with async with."""
    session_maker = get_session_maker()
    return session_maker()
