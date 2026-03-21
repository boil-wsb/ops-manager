"""
User schemas.
"""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str | None = None
    full_name: str | None = Field(None, max_length=100)
    is_active: bool = True

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        # Basic email format validation (less strict than EmailStr)
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, max_length=100)
    role_ids: list[int] = []


class UserUpdate(BaseModel):
    """User update schema."""
    email: str | None = None
    full_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None
    is_superuser: bool | None = None
    password: str | None = Field(None, min_length=8, max_length=100)
    role_ids: list[int] | None = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v


class UserInDB(UserBase):
    """User in database schema."""
    id: int
    is_superuser: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_superuser: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime
    permissions: list[str] = []


class UserLogin(BaseModel):
    """User login schema."""
    username: str
    password: str


class ChangePassword(BaseModel):
    """Change password schema."""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    permissions: list[str] = []
    user: UserResponse | None = None


class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)


class RoleCreate(RoleBase):
    """Role creation schema."""
    permissions: list[str] = []


class RoleResponse(RoleBase):
    """Role response schema."""
    id: int
    permissions: list[str]
    created_at: datetime
