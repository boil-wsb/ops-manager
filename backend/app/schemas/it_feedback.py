"""
IT Feedback schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ITFeedbackBase(BaseModel):
    """Base schema for IT feedback."""

    computer_type: str = Field(..., alias="computerType", min_length=1, max_length=20)
    usage_years: str = Field(..., alias="usageYears", min_length=1, max_length=20)
    lag_level: str = Field(..., alias="lagLevel", min_length=1, max_length=1)
    lag_scenarios: str | None = Field(None, alias="lagScenarios", max_length=500)
    description: str | None = Field(None, max_length=2000)
    contact: str | None = Field(None, max_length=100)
    client_ip: str | None = Field(None, alias="clientIp", max_length=45)
    status: str = Field(default="pending", max_length=20)
    resolved_by: str | None = Field(None, alias="resolvedBy", max_length=100)
    notes: str | None = Field(None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True)


class ITFeedbackCreate(BaseModel):
    """Schema for creating IT feedback."""

    computer_type: str = Field(..., alias="computerType")
    usage_years: str = Field(..., alias="usageYears")
    lag_level: str = Field(..., alias="lagLevel")
    lag_scenarios: str | None = Field(None, alias="lagScenarios")
    description: str | None = None
    contact: str | None = None
    client_ip: str | None = Field(None, alias="clientIp")
    status: str = "pending"

    model_config = ConfigDict(populate_by_name=True)


class ITFeedbackResponse(BaseModel):
    """Response schema for IT feedback."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    computer_type: str = Field(alias="computerType")
    usage_years: str = Field(alias="usageYears")
    lag_level: str = Field(alias="lagLevel")
    lag_scenarios: str | None = Field(None, alias="lagScenarios")
    description: str | None = None
    contact: str | None = None
    status: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    resolved_at: datetime | None = Field(None, alias="resolvedAt")
    resolved_by: str | None = Field(None, alias="resolvedBy")
    notes: str | None = None
    client_ip: str | None = Field(None, alias="clientIp")


class ITFeedbackListResponse(BaseModel):
    """List response for IT feedback."""

    total: int
    items: list[ITFeedbackResponse]
