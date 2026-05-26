"""
Authentication middleware for global API authentication.
"""

import ipaddress
from collections.abc import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from app.config import settings
from app.core.logging import get_logger
from app.core.security import verify_token
from app.crud.crud_user import crud_user
from app.db.session import get_async_session_local

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

logger.info(f"信任网络配置: {[str(n) for n in TRUSTED_NETWORKS]}", extra={"action": "auth.middleware"})
logger.info(f"认证排除路径: {AUTH_EXCLUDED_PATHS}", extra={"action": "auth.middleware"})


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return None


def _is_trusted_client(request: Request) -> bool:
    if not TRUSTED_NETWORKS:
        return False
    client_ip = _get_client_ip(request)
    if not client_ip:
        return False
    try:
        ip = ipaddress.ip_address(client_ip)
        return any(ip in network for network in TRUSTED_NETWORKS)
    except ValueError:
        return False


class AuthenticationMiddleware:
    """Middleware to handle global authentication for all API requests."""

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
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        path = request.url.path

        for exclude_path in self.EXCLUDE_PATHS:
            if path == exclude_path or path.startswith(exclude_path + "/"):
                return await call_next(request)

        is_trusted = _is_trusted_client(request)
        for excluded_path in AUTH_EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                if is_trusted:
                    logger.debug(f"信任网络跳过认证: {path}", extra={"action": "auth.bypass", "client_ip": _get_client_ip(request)})
                    return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ")[1]

        try:
            payload = verify_token(token)

            if payload is None:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or expired token"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if payload.get("type") != "access":
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid token type"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_id = payload.get("sub")
            if user_id is None:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid token payload"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            async with await get_async_session_local() as db:
                user = await crud_user.get(db, id=int(user_id))

                if not user:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "User not found"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                if not user.is_active:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "User is inactive"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                request.state.user = user

                response = await call_next(request)
                return response

        except Exception as e:
            logger.error(f"认证错误: {e}", extra={"action": "auth.middleware", "error": str(e)})
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication failed"},
                headers={"WWW-Authenticate": "Bearer"},
            )


def get_authentication_middleware():
    from starlette.middleware.base import BaseHTTPMiddleware

    class AuthenticationMiddlewareWrapper(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable):
            middleware = AuthenticationMiddleware()
            return await middleware.dispatch(request, call_next)

    return AuthenticationMiddlewareWrapper
