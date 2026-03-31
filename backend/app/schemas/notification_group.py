"""
Notification group schemas.
"""
from app.schemas.base import BaseResponse, BaseSchema


class UserBrief(BaseSchema):
    """Brief user info for notification group response."""
    id: int
    username: str
    full_name: str | None = None
    feishu_open_id: str | None = None


class NotificationGroupCreate(BaseSchema):
    """Schema for creating a notification group."""
    name: str
    description: str | None = None
    notification_type: str
    is_active: bool = True


class NotificationGroupUpdate(BaseSchema):
    """Schema for updating a notification group."""
    name: str | None = None
    description: str | None = None
    notification_type: str | None = None
    is_active: bool | None = None


class NotificationGroupResponse(BaseResponse):
    """Schema for notification group response."""
    name: str
    description: str | None = None
    notification_type: str
    is_active: bool
    members: list[UserBrief] = []


class NotificationGroupListResponse(BaseSchema):
    """Schema for notification group list response."""
    items: list[NotificationGroupResponse]
    total: int