"""
API router configuration.
"""
from fastapi import APIRouter

from app.api.v1 import auth, users, assets, ops, monitor

api_router = APIRouter()

# v1 API routes
api_router.include_router(auth.router, prefix="/v1", tags=["认证"])
api_router.include_router(users.router, prefix="/v1", tags=["用户"])
api_router.include_router(assets.router, prefix="/v1", tags=["资产"])
api_router.include_router(ops.router, prefix="/v1", tags=["运维"])
api_router.include_router(monitor.router, prefix="/v1", tags=["监控"])
