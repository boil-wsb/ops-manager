"""
API router configuration.
"""
from fastapi import APIRouter

from app.api.v1 import auth, users, assets, ops, monitor, permissions, roles, audit_logs, navigation, it_feedback

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/v1", tags=["认证"])
api_router.include_router(users.router, prefix="/v1", tags=["用户"])
api_router.include_router(roles.router, prefix="/v1", tags=["角色"])
api_router.include_router(permissions.router, prefix="/v1", tags=["权限"])
api_router.include_router(assets.router, prefix="/v1", tags=["资产"])
api_router.include_router(ops.router, prefix="/v1", tags=["运维"])
api_router.include_router(monitor.router, prefix="/v1", tags=["监控"])
api_router.include_router(audit_logs.router, prefix="/v1", tags=["审计日志"])
api_router.include_router(navigation.router, prefix="/v1", tags=["导航管理"])
api_router.include_router(it_feedback.router, prefix="/v1", tags=["IT反馈"])
