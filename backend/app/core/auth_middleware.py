"""
Authentication middleware for global API authentication.
"""
import logging
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.crud.crud_user import crud_user
from app.db.session import get_db

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthenticationMiddleware:
    """Middleware to handle global authentication for all API requests."""

    # Paths that don't require authentication
    EXCLUDE_PATHS = [
        "/health",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth",  # Auth endpoints
    ]

    @staticmethod
    async def get_db_session() -> AsyncSession:
        """Get database session."""
        async with await get_db() as db:
            yield db

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Dispatch request with authentication."""
        # Check if path is in exclude list
        path = request.url.path
        for exclude_path in self.EXCLUDE_PATHS:
            if path.startswith(exclude_path):
                return await call_next(request)

        # Get authorization credentials
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                content={"detail": "Not authenticated"},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract token
        token = auth_header.split(" ")[1]

        try:
            # Verify token
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

            # Get database session
            async with await get_db() as db:
                # Get user
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

                # Store user in request state
                request.state.user = user

                # Continue to next middleware
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
    """Get authentication middleware instance."""
    from starlette.middleware.base import BaseHTTPMiddleware

    class AuthenticationMiddlewareWrapper(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            middleware = AuthenticationMiddleware()
            return await middleware.dispatch(request, call_next)

    return AuthenticationMiddlewareWrapper
