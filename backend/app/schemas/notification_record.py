"""
Notification Record schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationRecordBase(BaseModel):
    """Base schema for Notification Record."""

    user: str = Field(..., min_length=1, max_length=100)
    matched_user: str | None = Field(None, max_length=100)
    feishu_open_id: str | None = Field(None, max_length=100)
    chat_id: str | None = Field(None, max_length=100)
    receive_type: str = Field("open_id", max_length=20)
    callback_id: str | None = Field(None, max_length=100)
    card_content: dict | None = None
    message_id: str | None = Field(None, max_length=100)
    success: bool = False
    error: str | None = Field(None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True)


class NotificationRecordCreate(BaseModel):
    """Schema for creating Notification Record."""

    user: str
    matched_user: str | None = None
    feishu_open_id: str | None = None
    chat_id: str | None = None
    receive_type: str = "open_id"
    callback_id: str | None = None
    open_message_id: str | None = None
    card_content: dict | None = None
    success: bool = False
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class NotificationRecordUpdate(BaseModel):
    """Schema for updating Notification Record."""

    callback_id: str | None = None
    message_id: str | None = None
    success: bool | None = None
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class NotificationRecordResponse(BaseModel):
    """Response schema for Notification Record."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user: str
    matched_user: str | None = None
    feishu_open_id: str | None = None
    chat_id: str | None = None
    receive_type: str = "open_id"
    callback_id: str | None = None
    open_message_id: str | None = None
    card_content: dict | None = None
    message_id: str | None = None
    success: bool
    error: str | None = None
    created_at: datetime


class NotificationRecordListResponse(BaseModel):
    """List response for Notification Records."""

    total: int
    items: list[NotificationRecordResponse]
