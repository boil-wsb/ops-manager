"""
Celery task utilities for async database sessions.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def get_celery_async_session():
    """
    Create a new async session factory for Celery tasks.

    Celery workers use fork mode, which can cause issues with shared
    database connections. This function creates a fresh engine and
    session factory for each task execution.
    """
    engine = create_async_engine(
        settings.async_database_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        echo=False,
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
