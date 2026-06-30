"""
Authentication middleware for global API authentication.

Uses pure ASGI middleware instead of BaseHTTPMiddleware to avoid
the known concurrency issues with BaseHTTPMiddleware that can
block other requests during async operations.
"""

import contextlib
import ipaddress
from collections.abc import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from app.config import settings
from app.core.logging import get_logger
from app.core.security import verify_token
from app.crud.crud_user import crud_user

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


def _parse_trusted_networks() -> list[ipaddress.IPv4Network]:
    networks = []
    raw = settings.auth_trusted_networks
    if not raw:
        return networks
    for cidr in raw.split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            logger.warning(f"无效的信任网络CIDR: {cidr}", extra={"action": "auth.middleware"})
    return networks


def _parse_excluded_paths() -> list[str]:
    paths = []
    raw = settings.auth_excluded_paths
    if not raw:
        return paths
    for p in raw.split(","):
        p = p.strip()
        if p:
            paths.append(p)
    return paths


TRUSTED_NETWORKS = _parse_trusted_networks()
AUTH_EXCLUDED_PATHS = _parse_excluded_paths()

logger.info(
    f"信任网络配置: {[str(n) for n in TRUSTED_NETWORKS]}", extra={"action": "auth.middleware"}
)
logger.info(
    f"认证排除路径: {AUTH_EXCLUDED_PATHS}",
    extra={"action": "auth.middleware"},
)


EXCLUDE_PATHS = [
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth",
    "/api/v1/navigation/public",
    "/api/v1/audit-logs",
    "/api/v1/it-feedback",
    "/api/v1/notification-records",
    "/api/v1/assets/users-for-owner",
    "/api/v1/labels",
    "/api/v1/feishu/notify",
    "/api/v1/it-reporter",
    "/api/v1/open-id",
    "/api/v1/alert/webhook/alertmanager",
]


def _get_client_ip(scope: dict) -> str | None:
    """Extract client IP from ASGI scope headers."""
    headers = dict(scope.get("headers", []))
    forwarded = headers.get(b"x-forwarded-for")
    if forwarded:
        return forwarded.decode().split(",")[0].strip()
    real_ip = headers.get(b"x-real-ip")
    if real_ip:
        return real_ip.decode().strip()
    client = scope.get("client")
    if client:
        return client[0]
    return None


def _is_trusted_client(scope: dict) -> bool:
    if not TRUSTED_NETWORKS:
        return False
    client_ip = _get_client_ip(scope)
    if not client_ip:
        return False
    try:
        ip = ipaddress.ip_address(client_ip)
        return any(ip in network for network in TRUSTED_NETWORKS)
    except ValueError:
        return False


class PureASGIAuthMiddleware:
    """Pure ASGI authentication middleware.

    Unlike BaseHTTPMiddleware, this does not block concurrent requests
    during async operations like database queries.
    """

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Check excluded paths
        for exclude_path in EXCLUDE_PATHS:
            if path == exclude_path or path.startswith(exclude_path + "/"):
                await self.app(scope, receive, send)
                return

        # Check trusted networks
        is_trusted = _is_trusted_client(scope)
        if is_trusted:
            for excluded_path in AUTH_EXCLUDED_PATHS:
                if path.startswith(excluded_path):
                    logger.debug(
                        f"信任网络跳过认证: {path}",
                        extra={"action": "auth.bypass", "client_ip": _get_client_ip(scope)},
                    )
                    await self.app(scope, receive, send)
                    return

        # Extract Authorization header from ASGI scope
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")
        if not auth_header:
            await self._send_unauthorized(send, "Not authenticated")
            return

        auth_str = auth_header.decode()
        if not auth_str.startswith("Bearer "):
            await self._send_unauthorized(send, "Not authenticated")
            return

        token = auth_str.split(" ", 1)[1]

        try:
            payload = verify_token(token)

            if payload is None:
                await self._send_unauthorized(send, "Invalid or expired token")
                return

            if payload.get("type") != "access":
                await self._send_unauthorized(send, "Invalid token type")
                return

            user_id = payload.get("sub")
            if user_id is None:
                await self._send_unauthorized(send, "Invalid token payload")
                return

            # Query user with retry for transient connection errors.
            # Only verify user exists and is active here — full user object
            # with roles will be loaded by downstream dependencies.
            # This avoids ORM relationship loading issues in middleware context.
            user_id_int = int(user_id)
            user_active = False
            import asyncio

            from sqlalchemy import select, text

            from app.db.session import get_session_maker
            from app.models.user import User

            session_maker = get_session_maker()

            for attempt in range(3):
                db = None
                try:
                    db = session_maker()
                    result = await db.execute(
                        select(User.id, User.is_active).where(User.id == user_id_int)
                    )
                    row = result.first()
                    if row and row.is_active:
                        user_active = True
                    await db.commit()
                except Exception as db_err:
                    if db:
                        with contextlib.suppress(Exception):
                            await db.rollback()
                    if attempt < 2:
                        logger.warning(
                            f"认证数据库查询失败，重试 {attempt + 1}/3: {db_err}",
                            extra={"action": "auth.middleware", "attempt": attempt + 1},
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    else:
                        logger.error(
                            f"认证数据库查询失败: {db_err}",
                            extra={"action": "auth.middleware", "error": str(db_err)},
                        )
                        await self._send_unauthorized(send, "Authentication failed")
                        return
                finally:
                    if db:
                        with contextlib.suppress(Exception):
                            await db.close()
                if user_active:
                    break

            if not user_active:
                await self._send_unauthorized(send, "User not found or inactive")
                return

            # Store authenticated user_id in scope state for downstream access.
            # The full User object will be loaded by downstream dependencies
            # (get_current_user) with proper session management and roles.
            scope.setdefault("state", {})
            if isinstance(scope["state"], dict):
                scope["state"]["user_id"] = user_id_int
            else:
                # FastAPI uses a State object
                from starlette.datastructures import State

                if not isinstance(scope.get("state"), State):
                    scope["state"] = State(scope.get("state", {}))
                scope["state"].user_id = user_id_int

            await self.app(scope, receive, send)

        except Exception as e:
            logger.error(f"认证错误: {e}", extra={"action": "auth.middleware", "error": str(e)})
            await self._send_unauthorized(send, "Authentication failed")

    async def _send_unauthorized(self, send: Callable, detail: str):
        """Send a 401 Unauthorized JSON response."""
        import json

        body = json.dumps({"detail": detail}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status.HTTP_401_UNAUTHORIZED,
            "headers": [
                [b"content-type", b"application/json"],
                [b"www-authenticate", b"Bearer"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
