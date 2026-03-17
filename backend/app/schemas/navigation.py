"""
Navigation link schemas.
"""
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema, BaseResponse


class NavigationLinkCreate(BaseSchema):
    """Schema for creating a navigation link."""
    category: str
    name: str
    url: str
    icon: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    restrict_to_current_role: bool = True


class NavigationLinkUpdate(BaseSchema):
    """Schema for updating a navigation link."""
    category: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    restrict_to_current_role: Optional[bool] = None


class RoleBrief(BaseSchema):
    """Brief role info for navigation link response."""
    id: int
    name: str


class NavigationLinkResponse(BaseResponse):
    """Schema for navigation link response."""
    category: str
    name: str
    url: str
    icon: Optional[str] = None
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    roles: List[RoleBrief] = []


class NavigationLinkListResponse(BaseSchema):
    """Schema for navigation link list response."""
    items: List[NavigationLinkResponse]
    total: int


class NavigationLinkGrouped(BaseSchema):
    """Schema for navigation links grouped by category."""
    category: str
    links: List[NavigationLinkResponse]
