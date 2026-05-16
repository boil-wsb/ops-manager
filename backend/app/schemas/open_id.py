from pydantic import BaseModel, Field


class OpenIdItem(BaseModel):
    full_name: str | None = Field(None, serialization_alias="fullName")
    username: str
    feishu_open_id: str | None = Field(None, serialization_alias="feishuOpenId")

    model_config = {"from_attributes": True, "populate_by_name": True}


class OpenIdResponse(BaseModel):
    items: list[OpenIdItem]
