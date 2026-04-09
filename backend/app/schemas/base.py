"""
Base schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema."""

    model_config = ConfigDict(from_attributes=True)


class BaseResponse(BaseSchema):
    """Base response schema."""

    id: int
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Pagination parameters."""

    page: int = 1
    page_size: int = 20


class PaginationResponse(BaseSchema):
    """Pagination response."""

    total: int
    page: int
    page_size: int
    pages: int


class ApiResponse(BaseSchema):
    """API response wrapper."""

    code: int = 0
    message: str = "success"
    data: dict | None = None
