from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SystemConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    group: str = Field(serialization_alias="group")
    description: str | None = None
    is_secret: bool = Field(serialization_alias="isSecret")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SystemConfigCreate(BaseModel):
    key: str
    value: str
    group: str
    description: str | None = None
    is_secret: bool = Field(False, validation_alias="isSecret")

    model_config = ConfigDict(populate_by_name=True)


class SystemConfigUpdate(BaseModel):
    value: str | None = None
    description: str | None = None
    is_secret: bool | None = Field(None, validation_alias="isSecret")

    model_config = ConfigDict(populate_by_name=True)


class SystemConfigListResponse(BaseModel):
    total: int
    items: list[SystemConfigResponse]
