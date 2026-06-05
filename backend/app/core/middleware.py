"""
Pure ASGI request logging middleware.

Replaces BaseHTTPMiddleware-based implementation to avoid
concurrency blocking issues inherent in BaseHTTPMiddleware.
"""

import time
import uuid
from collections.abc import Callable

from app.core.log_context import clear_request_context, set_request_context
from app.core.logging import get_logger

logger = get_logger(__name__)

SKIP_AUDIT_PATHS = frozenset({
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class PureASGILoggingMiddleware:
    """Pure ASGI request logging middleware.

    Unlike BaseHTTPMiddleware, this does not block concurrent requests
    and avoids the overhead of creating a separate task per request.
    """

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip logging for health check and docs
        if path in SKIP_AUDIT_PATHS:
            await self.app(scope, receive, send)
            return

        # Extract request info from ASGI scope
        request_id = uuid.uuid4().hex[:8]

        user_id = ""
        state = scope.get("state", {})
        if isinstance(state, dict):
            user = state.get("user")
        else:
            user = getattr(state, "user", None)
        if user is not None:
            username = getattr(user, "username", None)
            if username:
                user_id = username
            elif isinstance(user, dict):
                user_id = user.get("username", "")

        set_request_context(request_id=request_id, user_id=user_id)

        # Extract method, query string, client IP
        method = scope.get("method", "")
        query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")
        query = query_string if query_string else None
        client = scope.get("client")
        client_ip = client[0] if client else None

        logger.info(
            f"{method} {path} | IP: {client_ip} | 参数: {query or '无'}",
            extra={"action": "request.enter"},
        )

        start_time = time.time()
        response_status = 200

        async def send_with_status(message: dict):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
            await send(message)

        await self.app(scope, receive, send_with_status)

        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)

        user_str = f"用户: {user_id} | " if user_id else ""
        if response_status < 400:
            logger.info(
                f"{method} {path} | {user_str}状态: {response_status} | 耗时: {duration_ms}ms",
                extra={"action": "request.exit"},
            )
        elif response_status < 500:
            logger.warning(
                f"{method} {path} | {user_str}状态: {response_status} | 耗时: {duration_ms}ms | 客户端错误",
                extra={"action": "request.exit"},
            )
        else:
            logger.error(
                f"{method} {path} | {user_str}状态: {response_status} | 耗时: {duration_ms}ms | 服务器错误",
                extra={"action": "request.exit"},
            )

        clear_request_context()
