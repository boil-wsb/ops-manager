"""
Database session management.
"""

import asyncio
import contextlib
import threading
from functools import lru_cache

import asyncpg
from sqlalchemy import text
from sqlalchemy.exc import (
    DataError,
    DBAPIError,
    IntegrityError,
    ProgrammingError,
)
from sqlalchemy.exc import (
    InterfaceError as SAInterfaceError,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_NON_RETRYABLE_DB_ERRORS = (IntegrityError, ProgrammingError, DataError)

_TRANSIENT_ERRORS = (
    DBAPIError,
    SAInterfaceError,
    asyncpg.exceptions.PostgresError,
    asyncpg.exceptions.InterfaceError,
    ConnectionError,
    OSError,
)

_TRANSIENT_KEYWORDS = (
    "connection",
    "closed",
    "interface",
    "timeout",
    "broken pipe",
)

_pool_dispose_lock = asyncio.Lock()
_last_pool_dispose_time = 0.0
_POOL_DISPOSE_COOLDOWN = 30.0

# Thread-local storage for scheduler threads. When a scheduler thread
# initializes its own engine (via create_scheduler_engine), it stores
# the session_maker here. db_operation_with_retry checks this first.
_scheduler_thread_local = threading.local()


@lru_cache
def get_engine():
    """Get or create the async engine (lazy initialization)."""
    return create_async_engine(
        settings.async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=180,
        pool_timeout=10,
        connect_args={
            "timeout": 10,
            "command_timeout": 30,
            "server_settings": {
                "tcp_keepalives_idle": "15",
                "tcp_keepalives_interval": "5",
                "tcp_keepalives_count": "3",
            },
        },
        echo=False,
    )


def create_scheduler_engine():
    """Create a separate async engine for scheduler threads.

    Scheduler threads run in their own event loops (BackgroundScheduler).
    asyncpg connections are bound to the event loop that created them,
    so sharing the main API engine causes "Connection was closed" errors.

    This engine has a smaller pool since scheduler tasks are less concurrent
    than API requests, and is fully independent from the main API engine.
    """
    return create_async_engine(
        settings.async_database_url,
        pool_size=5,
        max_overflow=3,
        pool_pre_ping=True,
        pool_recycle=180,
        pool_timeout=10,
        connect_args={
            "timeout": 10,
            "command_timeout": 30,
            "server_settings": {
                "tcp_keepalives_idle": "15",
                "tcp_keepalives_interval": "5",
                "tcp_keepalives_count": "3",
            },
        },
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


def _is_transient_error(e: Exception) -> bool:
    if isinstance(e, _TRANSIENT_ERRORS):
        return True
    err_msg = str(e).lower()
    err_type = type(e).__name__.lower()
    return any(kw in err_msg or kw in err_type for kw in _TRANSIENT_KEYWORDS)


async def _dispose_pool_safely():
    import time as _time

    global _last_pool_dispose_time
    now = _time.monotonic()
    if now - _last_pool_dispose_time < _POOL_DISPOSE_COOLDOWN:
        logger.debug("连接池清理冷却中，跳过", extra={"action": "db.pool"})
        return
    async with _pool_dispose_lock:
        now = _time.monotonic()
        if now - _last_pool_dispose_time < _POOL_DISPOSE_COOLDOWN:
            return
        try:
            engine = get_engine()
            await engine.dispose()
            _last_pool_dispose_time = now
            logger.warning("连接池已清理（瞬态错误触发）", extra={"action": "db.pool"})
        except Exception as e:
            logger.debug(f"清理连接池时出错: {e}", extra={"action": "db.pool"})


async def db_operation_with_retry(operation, max_retries=2, retry_delay=1.0):
    """Execute a DB operation with automatic retry on transient connection errors.

    Each retry creates a brand-new session from the pool, so stale connections
    are never reused across attempts. Uses exponential backoff between retries.

    When called from a scheduler thread (detected via threading.local), uses
    the thread-local session maker instead of the shared one. This avoids
    cross-event-loop asyncpg connection issues.

    Args:
        operation: async callable that receives a db session and returns a result.
        max_retries: maximum number of retries (default 2).
        retry_delay: base seconds to wait between retries (default 1.0).
                     Actual delay = retry_delay * (2 ** attempt).

    Returns:
        The result of the operation.

    Raises:
        The last transient error if all retries are exhausted.
        Any non-transient error immediately without retry.
    """
    # Check for scheduler thread-local session maker
    scheduler_sm = getattr(_scheduler_thread_local, "session_maker", None)
    session_maker = scheduler_sm if scheduler_sm else get_session_maker()
    last_error = None

    for attempt in range(max_retries + 1):
        need_retry = False
        try:
            async with session_maker() as db:
                try:
                    return await operation(db)
                except _NON_RETRYABLE_DB_ERRORS:
                    with contextlib.suppress(Exception):
                        await db.rollback()
                    raise
                except asyncio.CancelledError:
                    raise
                except _TRANSIENT_ERRORS as e:
                    last_error = e
                    with contextlib.suppress(Exception):
                        await db.rollback()
                    need_retry = True
                except Exception as e:
                    if _is_transient_error(e):
                        last_error = e
                        with contextlib.suppress(Exception):
                            await db.rollback()
                        need_retry = True
                    else:
                        with contextlib.suppress(Exception):
                            await db.rollback()
                        raise
        except asyncio.CancelledError:
            raise
        except _TRANSIENT_ERRORS as e:
            last_error = e
            need_retry = True
        except Exception as e:
            if _is_transient_error(e):
                last_error = e
                need_retry = True
            else:
                raise

        if need_retry:
            if attempt < max_retries:
                delay = retry_delay * (2**attempt)
                logger.warning(
                    f"DB 连接错误，第 {attempt + 1} 次重试（等待 {delay}s）: {type(last_error).__name__}: {last_error}",
                    extra={"action": "db.retry", "attempt": attempt + 1},
                )
                await asyncio.sleep(delay)
                continue
            else:
                raise last_error

    raise last_error


async def ensure_pool_health():
    """Check connection pool health and dispose stale connections if needed.

    In scheduler threads, checks the thread-local engine instead of the
    shared one to avoid cross-event-loop issues.
    """
    scheduler_engine = getattr(_scheduler_thread_local, "engine", None)
    engine = scheduler_engine if scheduler_engine else get_engine()
    pool = engine.pool
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pool_status = f"size={pool.size()}, checked_in={pool.checkedin()}, checked_out={pool.checkedout()}, overflow={pool.overflow()}"
        logger.debug(f"连接池健康检查通过: {pool_status}", extra={"action": "db.health"})
    except Exception as e:
        logger.warning(
            f"连接池健康检查失败，正在清理: {e}",
            extra={"action": "db.health"},
        )
        await engine.dispose()
        logger.info(
            "连接池已清理重建",
            extra={"action": "db.health"},
        )


def log_pool_status():
    """Log current connection pool status for diagnostics.

    In scheduler threads, logs the thread-local engine's pool instead of
    the shared one.
    """
    scheduler_engine = getattr(_scheduler_thread_local, "engine", None)
    engine = scheduler_engine if scheduler_engine else get_engine()
    pool = engine.pool
    logger.info(
        f"连接池状态: size={pool.size()}, checked_in={pool.checkedin()}, "
        f"checked_out={pool.checkedout()}, overflow={pool.overflow()}",
        extra={"action": "db.pool"},
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
