"""
Permission and Role schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Permission Schemas
class PermissionBase(BaseModel):
    """Base permission schema."""
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    module: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class PermissionCreate(PermissionBase):
    """Permission creation schema."""
    pass


class PermissionUpdate(BaseModel):
    """Permission update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class PermissionResponse(PermissionBase):
    """Permission response schema."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PermissionModule(BaseModel):
    """Permission module schema."""
    code: str
    name: str


# Role Schemas
class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class RoleCreate(RoleBase):
    """Role creation schema."""
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    """Role update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """Role response schema."""
    id: int
    is_system: bool
    permission_count: int = 0
    user_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleDetailResponse(RoleBase):
    """Role detail response schema with permissions."""
    id: int
    is_system: bool
    permissions: List[PermissionResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RolePermissionUpdate(BaseModel):
    """Role permission update schema."""
    permission_ids: List[int]


class RolePermissionResponse(BaseModel):
    """Role permission response schema."""
    role_id: int
    permissions: List[PermissionResponse]
    permission_count: int


# User Role Schemas
class UserRoleUpdate(BaseModel):
    """User role update schema."""
    role_ids: List[int]


class UserRoleResponse(BaseModel):
    """User role response schema."""
    user_id: int
    roles: List[RoleResponse]


class UserPermissionsResponse(BaseModel):
    """User permissions response schema."""
    user_id: int
    permissions: List[str]
    permission_tree: dict
