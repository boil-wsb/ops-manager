"""
Authentication middleware for global API authentication.
"""

import ipaddress
import logging
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import verify_token
from app.crud.crud_user import crud_user
from app.db.session import get_db

logger = logging.getLogger(__name__)

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
            logger.warning(f"Invalid trusted network CIDR: {cidr}")
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
    ]

    @staticmethod
    async def get_db_session() -> AsyncSession:
        async with await get_db() as db:
            yield db

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        for exclude_path in self.EXCLUDE_PATHS:
            if path.startswith(exclude_path):
                return await call_next(request)

        for excluded_path in AUTH_EXCLUDED_PATHS:
            if path.startswith(excluded_path) and _is_trusted_client(request):
                logger.debug(f"Trusted network auth bypass: {path} from {_get_client_ip(request)}")
                return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                content={"detail": "Not authenticated"},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ")[1]

        try:
            payload = verify_token(token)

            if payload is None:
                return Response(
                    content={"detail": "Invalid or expired token"},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if payload.get("type") != "access":
                return Response(
                    content={"detail": "Invalid token type"},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_id = payload.get("sub")
            if user_id is None:
                return Response(
                    content={"detail": "Invalid token payload"},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Bearer"},
                )

            async with await get_db() as db:
                user = await crud_user.get(db, id=int(user_id))

                if not user:
                    return Response(
                        content={"detail": "User not found"},
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                if not user.is_active:
                    return Response(
                        content={"detail": "User is inactive"},
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                request.state.user = user

                response = await call_next(request)
                return response

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return Response(
                content={"detail": "Authentication failed"},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )


def get_authentication_middleware():
    from starlette.middleware.base import BaseHTTPMiddleware

    class AuthenticationMiddlewareWrapper(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            middleware = AuthenticationMiddleware()
            return await middleware.dispatch(request, call_next)

    return AuthenticationMiddlewareWrapper
