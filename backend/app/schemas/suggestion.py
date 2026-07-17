"""
Suggestion schemas for anonymous suggestions.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SuggestionCreate(BaseModel):
    """Schema for submitting an anonymous suggestion."""

    content: str = Field(..., min_length=1, max_length=2000, description="意见内容")
    highlights: str | None = Field(None, max_length=2000, description="项目服务亮点")
    innovation_ideas: str | None = Field(
        None, alias="innovationIdeas", max_length=2000, description="创新/团队协助效能提高idea"
    )
    department_id: int | None = Field(None, alias="departmentId", description="指派部门ID(单选)")
    assignee_user_id: int | None = Field(None, alias="assigneeUserId", description="指派人用户ID(单选)")

    model_config = ConfigDict(populate_by_name=True)


class SuggestionSubmitResponse(BaseModel):
    """Response after submitting a suggestion (no submitter info exposed)."""

    query_code: str = Field(..., alias="queryCode", description="匿名查询码")
    message: str = Field(..., description="提示信息")

    model_config = ConfigDict(populate_by_name=True)


class AssignmentResponse(BaseModel):
    """Response schema for a suggestion assignment."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    suggestion_id: int = Field(..., alias="suggestionId")
    department_id: int | None = Field(None, alias="departmentId")
    department_name: str | None = Field(None, alias="departmentName")
    assignee_user_id: int | None = Field(None, alias="assigneeUserId")
    assignee_name: str | None = Field(None, alias="assigneeName")
    assignee_open_id: str | None = Field(None, alias="assigneeOpenId")
    open_message_id: str | None = Field(None, alias="openMessageId")
    status: str
    reviewed_at: datetime | None = Field(None, alias="reviewedAt")
    review_comment: str | None = Field(None, alias="reviewComment")


class SuggestionResponse(BaseModel):
    """Response schema for a suggestion (no submitter info exposed)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    content: str
    highlights: str | None = None
    innovation_ideas: str | None = Field(None, alias="innovationIdeas")
    status: str
    query_code: str = Field(..., alias="queryCode")
    market_result: str | None = Field(None, alias="marketResult")
    archived_at: datetime | None = Field(None, alias="archivedAt")
    reject_reason: str | None = Field(None, alias="rejectReason")
    rejected_at: datetime | None = Field(None, alias="rejectedAt")
    created_at: datetime = Field(..., alias="createdAt")
    assignments: list[AssignmentResponse] = []


class SuggestionListResponse(BaseModel):
    """List response for suggestions."""

    model_config = ConfigDict(populate_by_name=True)

    total: int
    items: list[SuggestionResponse]
    page: int = Field(1, alias="page")
    page_size: int = Field(20, alias="pageSize")
    total_pages: int = Field(1, alias="totalPages")


class SuggestionTrackResponse(BaseModel):
    """Track response (by query_code, minimal info)."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    status_text: str = Field(..., alias="statusText")
    created_at: datetime = Field(..., alias="createdAt")
    archived_at: datetime | None = Field(None, alias="archivedAt")
    market_result: str | None = Field(None, alias="marketResult")
    reject_reason: str | None = Field(None, alias="rejectReason")


class SuggestionArchiveIn(BaseModel):
    """Input for market team archiving a suggestion."""

    market_result: str = Field(..., alias="marketResult", min_length=1, max_length=2000)

    model_config = ConfigDict(populate_by_name=True)
