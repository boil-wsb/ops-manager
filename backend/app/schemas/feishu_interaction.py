from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeishuInteractionCreate(BaseModel):
    direction: str = Field(..., max_length=20)
    interaction_type: str = Field(..., max_length=30)
    user_id: int | None = None
    feishu_open_id: str | None = Field(None, max_length=100)
    message_id: str | None = Field(None, max_length=100)
    chat_id: str | None = Field(None, max_length=100)
    content: dict[str, Any] | None = None
    msg_type: str | None = Field(None, max_length=30)
    action_type: str | None = Field(None, max_length=100)
    related_type: str | None = Field(None, max_length=50)
    related_id: str | None = Field(None, max_length=100)
    status: str = Field("success", max_length=20)
    error: str | None = Field(None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True)


class FeishuInteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    direction: str
    interaction_type: str
    user_id: int | None = None
    feishu_open_id: str | None = None
    message_id: str | None = None
    chat_id: str | None = None
    content: dict[str, Any] | None = None
    msg_type: str | None = None
    action_type: str | None = None
    related_type: str | None = None
    related_id: str | None = None
    status: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class FeishuInteractionListResponse(BaseModel):
    total: int
    items: list[FeishuInteractionResponse]
