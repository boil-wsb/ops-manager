from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationCallbackLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    notification_record_id: int | None = None
    callback_url: str
    request_body: dict | None = None
    response_status: int | None = None
    response_body: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime


class NotificationCallbackLogListResponse(BaseModel):
    total: int
    items: list[NotificationCallbackLogResponse]
    page: int
    page_size: int
