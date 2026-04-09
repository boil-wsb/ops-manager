"""
Request logging middleware.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""

    SKIP_AUDIT_PATHS = [
        "/health",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    AUDIT_READ_PATHS = [
        "/api/v1/users",
        "/api/v1/roles",
        "/api/v1/assets",
        "/api/v1/permissions",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.SKIP_AUDIT_PATHS:
            return await call_next(request)

        start_time = time.time()

        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else None
        client_ip = request.client.host if request.client else None

        logger.info(f"[请求] {method} {path} | IP: {client_ip} | 参数: {query or '无'}")

        response = await call_next(request)

        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)

        user_info = None
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "username"):
                user_info = user.username
            elif isinstance(user, dict):
                user_info = user.get("username", None)

        user_str = f"用户: {user_info} | " if user_info else ""
        if response.status_code < 400:
            logger.info(
                f"[响应] {method} {path} | {user_str}状态: {response.status_code} | 耗时: {duration_ms}ms"
            )
        elif response.status_code < 500:
            logger.warning(
                f"[响应] {method} {path} | {user_str}状态: {response.status_code} | 耗时: {duration_ms}ms | 客户端错误"
            )
        else:
            logger.error(
                f"[响应] {method} {path} | {user_str}状态: {response.status_code} | 耗时: {duration_ms}ms | 服务器错误"
            )

        return response
