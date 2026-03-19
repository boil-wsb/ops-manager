"""
IT Feedback schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ITFeedbackBase(BaseModel):
    """Base schema for IT feedback."""
    computer_type: str = Field(..., alias="computerType", min_length=1, max_length=20)
    usage_years: str = Field(..., alias="usageYears", min_length=1, max_length=20)
    lag_level: str = Field(..., alias="lagLevel", min_length=1, max_length=1)
    lag_scenarios: Optional[str] = Field(None, alias="lagScenarios", max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    contact: Optional[str] = Field(None, max_length=100)
    client_ip: Optional[str] = Field(None, alias="clientIp", max_length=45)
    status: str = Field(default="pending", max_length=20)
    resolved_by: Optional[str] = Field(None, alias="resolvedBy", max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True)


class ITFeedbackCreate(BaseModel):
    """Schema for creating IT feedback."""
    computer_type: str = Field(..., alias="computerType")
    usage_years: str = Field(..., alias="usageYears")
    lag_level: str = Field(..., alias="lagLevel")
    lag_scenarios: Optional[str] = Field(None, alias="lagScenarios")
    description: Optional[str] = None
    contact: Optional[str] = None
    client_ip: Optional[str] = Field(None, alias="clientIp")
    status: str = "pending"

    model_config = ConfigDict(populate_by_name=True)


class ITFeedbackResponse(BaseModel):
    """Response schema for IT feedback."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: int
    computer_type: str = Field(alias="computerType")
    usage_years: str = Field(alias="usageYears")
    lag_level: str = Field(alias="lagLevel")
    lag_scenarios: Optional[str] = Field(None, alias="lagScenarios")
    description: Optional[str] = None
    contact: Optional[str] = None
    status: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    resolved_at: Optional[datetime] = Field(None, alias="resolvedAt")
    resolved_by: Optional[str] = Field(None, alias="resolvedBy")
    notes: Optional[str] = None
    client_ip: Optional[str] = Field(None, alias="clientIp")


class ITFeedbackListResponse(BaseModel):
    """List response for IT feedback."""
    total: int
    items: List[ITFeedbackResponse]
