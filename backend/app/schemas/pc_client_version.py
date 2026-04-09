"""
Pydantic schemas for PC Client Version.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class PCClientVersionBase(BaseModel):
    """Base schema for PC Client Version."""

    version: Annotated[str, Field(max_length=20)]
    release_notes: str | None = None
    download_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True
    force_update: bool = False
    min_version: str | None = Field(default=None, max_length=20)
    file_count: int = 0


class PCClientVersionCreate(PCClientVersionBase):
    """Schema for creating PC Client Version."""

    pass


class PCClientVersionUpdate(BaseModel):
    """Schema for updating PC Client Version."""

    version: Annotated[str, Field(max_length=20)] | None = None
    release_notes: str | None = None
    download_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    force_update: bool | None = None
    min_version: str | None = Field(default=None, max_length=20)
    file_count: int | None = None


class PCClientVersionResponse(PCClientVersionBase):
    """Schema for PC Client Version response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PCClientVersionCheckResponse(BaseModel):
    """Schema for version check response (used by VBS script)."""

    version: str
    releaseNotes: str | None = None  # noqa: N815
    downloadUrl: str | None = None  # noqa: N815
    files: list[dict] | None = None
