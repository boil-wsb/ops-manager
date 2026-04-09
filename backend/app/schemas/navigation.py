"""
Navigation link schemas.
"""

from app.schemas.base import BaseResponse, BaseSchema


class NavigationLinkCreate(BaseSchema):
    """Schema for creating a navigation link."""

    category: str
    name: str
    url: str
    icon: str | None = None
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True
    restrict_to_current_role: bool = True


class NavigationLinkUpdate(BaseSchema):
    """Schema for updating a navigation link."""

    category: str | None = None
    name: str | None = None
    url: str | None = None
    icon: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    restrict_to_current_role: bool | None = None


class RoleBrief(BaseSchema):
    """Brief role info for navigation link response."""

    id: int
    name: str


class NavigationLinkResponse(BaseResponse):
    """Schema for navigation link response."""

    category: str
    name: str
    url: str
    icon: str | None = None
    description: str | None = None
    sort_order: int
    is_active: bool
    roles: list[RoleBrief] = []


class NavigationLinkListResponse(BaseSchema):
    """Schema for navigation link list response."""

    items: list[NavigationLinkResponse]
    total: int


class NavigationLinkGrouped(BaseSchema):
    """Schema for navigation links grouped by category."""

    category: str
    links: list[NavigationLinkResponse]


class NavigationLinkImport(BaseSchema):
    """Schema for importing a navigation link from CSV."""

    category: str
    name: str
    url: str
    icon: str | None = None
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True
    role_names: str | None = None


class NavigationLinkImportResult(BaseSchema):
    """Schema for import result."""

    success: bool
    name: str
    message: str


class NavigationImportResponse(BaseSchema):
    """Schema for bulk import response."""

    total: int
    success_count: int
    failed_count: int
    results: list[NavigationLinkImportResult]
