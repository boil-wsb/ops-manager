"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config import settings
from app.core.logging import get_logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import limiter
from app.core.redis import close_redis, init_redis
from app.db.init_db import init_db
from app.startup.pc_versions import sync_pc_versions_on_startup
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting up application: {settings.app_name} v{settings.app_version}")

    try:
        logger.info("Checking database initialization...")
        await init_db()
        logger.info("Database initialization check completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    try:
        await init_redis()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")

    try:
        async with AsyncSessionLocal() as db:
            synced = await sync_pc_versions_on_startup(db)
            if synced:
                logger.info(f"PC client versions synced: {synced}")
            else:
                logger.info("No new PC client versions to sync")
    except Exception as e:
        logger.error(f"PC versions sync failed: {e}")

    yield

    logger.info("Shutting down application")

    try:
        await close_redis()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")


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
