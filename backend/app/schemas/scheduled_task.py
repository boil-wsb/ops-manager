from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScheduledTaskResponse(BaseModel):
    id: int
    task_id: str = Field(serialization_alias="taskId")
    name: str
    task_function: str = Field(serialization_alias="taskFunction")
    trigger_type: str = Field(serialization_alias="triggerType")
    trigger_config: dict[str, Any] = Field(serialization_alias="triggerConfig")
    is_enabled: bool = Field(serialization_alias="isEnabled")
    description: str | None = None
    category: str
    last_run_at: datetime | None = Field(None, serialization_alias="lastRunAt")
    last_run_status: str | None = Field(None, serialization_alias="lastRunStatus")
    last_run_duration: float | None = Field(None, serialization_alias="lastRunDuration")
    next_run_time: datetime | None = Field(None, serialization_alias="nextRunTime")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ScheduledTaskUpdate(BaseModel):
    name: str | None = None
    trigger_config: dict[str, Any] | None = Field(None, validation_alias="triggerConfig")
    is_enabled: bool | None = Field(None, validation_alias="isEnabled")
    description: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class TaskExecutionLogResponse(BaseModel):
    id: int
    task_id: str = Field(serialization_alias="taskId")
    status: str
    started_at: datetime = Field(serialization_alias="startedAt")
    finished_at: datetime | None = Field(None, serialization_alias="finishedAt")
    duration: float | None = None
    error_message: str | None = Field(None, serialization_alias="errorMessage")
    result_summary: str | None = Field(None, serialization_alias="resultSummary")
    trigger_type: str = Field(serialization_alias="triggerType")
    triggered_by: str | None = Field(None, serialization_alias="triggeredBy")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TaskRunResponse(BaseModel):
    status: str
    duration: float | None = None
    error_message: str | None = Field(None, serialization_alias="errorMessage")
    result_summary: str | None = Field(None, serialization_alias="resultSummary")


class ScheduledTaskListResponse(BaseModel):
    total: int
    items: list[ScheduledTaskResponse]


class TaskExecutionLogListResponse(BaseModel):
    total: int
    items: list[TaskExecutionLogResponse]
