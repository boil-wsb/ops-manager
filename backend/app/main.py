"""
FastAPI application entry point.
"""

import asyncio
import warnings
from contextlib import asynccontextmanager
from typing import Any, NamedTuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config import settings
from app.core.auth_middleware import get_authentication_middleware
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import limiter
from app.core.redis import close_redis, init_redis
from app.db.init_db import init_db
from app.integrations.feishu.callback_handler import start_feishu_callback_client
from app.scheduler import start_scheduler, stop_scheduler
from app.startup.pc_versions import sync_pc_versions_on_startup

logger = get_logger(__name__)

configure_logging()

warnings.filterwarnings("ignore", message=".*alias.*Field.*")


class TaskResult(NamedTuple):
    name: str
    success: bool
    result: Any
    error: Exception | None


async def _run_task(name: str, coro: Any) -> TaskResult:
    """Run a task with independent error handling."""
    try:
        result = await coro
        return TaskResult(name, True, result, None)
    except Exception as e:
        logger.error(
            f"{name} 失败: {e}", extra={"action": "app.startup", "task": name, "error": str(e)}
        )
        return TaskResult(name, False, None, e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(
        f"应用启动: {settings.app_name} v{settings.app_version}",
        extra={
            "action": "app.startup",
            "app_name": settings.app_name,
            "version": settings.app_version,
        },
    )

    async def _init_db_task():
        await init_db()
        logger.info("数据库初始化检查完成", extra={"action": "app.startup"})

    async def _init_redis_task():
        await init_redis()
        logger.info("Redis连接已初始化", extra={"action": "app.startup"})

    async def _sync_pc_versions_task():
        from app.db.session import get_async_session_local

        async with await get_async_session_local() as db:
            synced = await sync_pc_versions_on_startup(db)
            if synced:
                logger.info(
                    f"PC客户端版本已同步: {synced}",
                    extra={"action": "app.startup", "synced": synced},
                )
            else:
                logger.info("无新PC客户端版本需同步", extra={"action": "app.startup"})
            return synced

    results = await asyncio.gather(
        _run_task("Database initialization", _init_db_task()),
        _run_task("Redis initialization", _init_redis_task()),
        _run_task("PC versions sync", _sync_pc_versions_task()),
    )

    for result in results:
        if not result.success:
            logger.warning(
                f"启动任务 '{result.name}' 失败，继续启动流程",
                extra={"action": "app.startup", "task": result.name},
            )

    start_feishu_callback_client()
    start_scheduler()

    yield

    logger.info("应用关闭中", extra={"action": "app.shutdown"})
    stop_scheduler()

    try:
        await close_redis()
        logger.info("Redis连接已关闭", extra={"action": "app.shutdown"})
    except Exception as e:
        logger.error(f"关闭Redis连接失败: {e}", extra={"action": "app.shutdown", "error": str(e)})


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="OpsManager V2 - Modern Operations Management Platform",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

# Add authentication middleware
AuthenticationMiddleware = get_authentication_middleware()
app.add_middleware(AuthenticationMiddleware)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
    }
