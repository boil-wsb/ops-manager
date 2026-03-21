"""
Custom exceptions for the application.
"""
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str = "ERROR",
        headers: dict = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


class AuthenticationError(AppException):
    """Authentication error."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code="AUTHENTICATION_ERROR",
            headers={"WWW-Authenticate": "Bearer"}
        )


class PermissionDeniedError(AppException):
    """Permission denied error."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code="PERMISSION_DENIED"
        )


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code="NOT_FOUND"
        )


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="VALIDATION_ERROR"
        )


class ConflictError(AppException):
    """Resource conflict error."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            code="CONFLICT"
        )
