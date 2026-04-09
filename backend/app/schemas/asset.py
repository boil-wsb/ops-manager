"""
Asset schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LabelBase(BaseModel):
    """Base label schema."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#1890ff", max_length=7)
    description: str | None = Field(None, max_length=255)


class LabelCreate(LabelBase):
    """Label creation schema."""

    pass


class LabelResponse(LabelBase):
    """Label response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class OwnerResponse(BaseModel):
    """Owner response schema for nested owner info."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str | None = None


class AssetBase(BaseModel):
    """Base asset schema."""

    asset_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    asset_type: str = Field(..., pattern="^(SERVER|VM|NETWORK|STORAGE|TERMINAL)$")
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|OFFLINE|MAINTENANCE|RETIRED)$")

    # Network info
    ip_address: str | None = Field(None, max_length=45)
    private_ip: str | None = Field(None, max_length=45)
    mac_address: str | None = Field(None, max_length=17)

    # Hardware info
    cpu_cores: int | None = Field(None, ge=1)
    memory_gb: int | None = Field(None, ge=1)
    disk_gb: int | None = Field(None, ge=1)
    os_type: str | None = Field(None, max_length=50)
    os_version: str | None = Field(None, max_length=100)
    arch: str | None = Field(None, max_length=50)

    # Terminal specific info
    hostname: str | None = Field(None, max_length=100)
    serial_number: str | None = Field(None, max_length=100)
    uuid: str | None = Field(None, max_length=100)
    customer: str | None = Field(None, max_length=100)

    # Location info
    idc: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    rack: str | None = Field(None, max_length=50)

    # Metadata
    description: str | None = None


class AssetCreate(AssetBase):
    """Asset creation schema."""

    label_ids: list[int] = []
    owner_name: str | None = Field(None, max_length=100)
    owner_id: int | None = None


class AssetUpdate(BaseModel):
    """Asset update schema."""

    name: str | None = Field(None, min_length=1, max_length=200)
    status: str | None = Field(None, pattern="^(ACTIVE|OFFLINE|MAINTENANCE|RETIRED)$")

    ip_address: str | None = Field(None, max_length=45)
    private_ip: str | None = Field(None, max_length=45)
    mac_address: str | None = Field(None, max_length=17)

    cpu_cores: int | None = Field(None, ge=1)
    memory_gb: int | None = Field(None, ge=1)
    disk_gb: int | None = Field(None, ge=1)
    os_type: str | None = Field(None, max_length=50)
    os_version: str | None = Field(None, max_length=100)

    idc: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    rack: str | None = Field(None, max_length=50)

    description: str | None = None
    owner_name: str | None = Field(None, max_length=100)
    owner_id: int | None = None
    label_ids: list[int] | None = None


class AssetResponse(AssetBase):
    """Asset response schema."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=lambda x: "".join(
            word.capitalize() if i else word for i, word in enumerate(x.split("_"))
        ),
        populate_by_name=True,
    )

    id: int
    labels: list[LabelResponse] = []
    owner_id: int | None = None
    owner: OwnerResponse | None = None
    owner_name: str | None = None
    created_at: datetime
    updated_at: datetime
    # Prometheus sync fields
    source: str | None = None
    prometheus_instance: str | None = None
    last_sync_time: datetime | None = None
    sync_status: str | None = None
    # Additional fields
    cpu_cores: int | None = None
    memory_gb: int | None = None
    disk_gb: int | None = None
    # All pc_info labels for terminals
    labels_data: dict[str, Any] | None = None


class AssetListResponse(BaseModel):
    """Asset list response with pagination."""

    total: int
    items: list[AssetResponse]


class AssetHistoryResponse(BaseModel):
    """Asset history response."""

    id: int
    asset_id: int
    action: str
    changes: dict[str, Any] | None
    operator_id: int | None
    created_at: datetime


class AssetTreeNode(BaseModel):
    """Asset tree node for hierarchical display."""

    key: str
    title: str
    children: list["AssetTreeNode"] | None = None
    is_leaf: bool = False
    data: dict[str, Any] | None = None


class AssetFilter(BaseModel):
    """Asset filter parameters."""

    asset_type: str | None = None
    status: str | None = None
    idc: str | None = None
    keyword: str | None = None
    label_ids: list[int] | None = None
