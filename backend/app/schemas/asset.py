"""
Asset schemas.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponse


class LabelBase(BaseModel):
    """Base label schema."""
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#1890ff", max_length=7)
    description: Optional[str] = Field(None, max_length=255)


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
    name: Optional[str] = None


class AssetBase(BaseModel):
    """Base asset schema."""
    asset_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    asset_type: str = Field(..., pattern="^(SERVER|VM|NETWORK|STORAGE|TERMINAL)$")
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|OFFLINE|MAINTENANCE|RETIRED)$")
    
    # Network info
    ip_address: Optional[str] = Field(None, max_length=45)
    private_ip: Optional[str] = Field(None, max_length=45)
    mac_address: Optional[str] = Field(None, max_length=17)
    
    # Hardware info
    cpu_cores: Optional[int] = Field(None, ge=1)
    memory_gb: Optional[int] = Field(None, ge=1)
    disk_gb: Optional[int] = Field(None, ge=1)
    os_type: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=100)
    arch: Optional[str] = Field(None, max_length=50)
    
    # Terminal specific info
    hostname: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    uuid: Optional[str] = Field(None, max_length=100)
    customer: Optional[str] = Field(None, max_length=100)
    
    # Location info
    idc: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    rack: Optional[str] = Field(None, max_length=50)
    
    # Metadata
    description: Optional[str] = None


class AssetCreate(AssetBase):
    """Asset creation schema."""
    label_ids: List[int] = []


class AssetUpdate(BaseModel):
    """Asset update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = Field(None, pattern="^(ACTIVE|OFFLINE|MAINTENANCE|RETIRED)$")
    
    ip_address: Optional[str] = Field(None, max_length=45)
    private_ip: Optional[str] = Field(None, max_length=45)
    mac_address: Optional[str] = Field(None, max_length=17)
    
    cpu_cores: Optional[int] = Field(None, ge=1)
    memory_gb: Optional[int] = Field(None, ge=1)
    disk_gb: Optional[int] = Field(None, ge=1)
    os_type: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=100)
    
    idc: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    rack: Optional[str] = Field(None, max_length=50)
    
    description: Optional[str] = None
    label_ids: Optional[List[int]] = None


class AssetResponse(AssetBase):
    """Asset response schema."""
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=lambda x: ''.join(word.capitalize() if i else word for i, word in enumerate(x.split('_'))),
        populate_by_name=True
    )

    id: int
    labels: List[LabelResponse] = []
    owner_id: Optional[int] = None
    owner: Optional[OwnerResponse] = None
    created_at: datetime
    updated_at: datetime
    # Prometheus sync fields
    source: Optional[str] = None
    prometheus_instance: Optional[str] = None
    last_sync_time: Optional[datetime] = None
    sync_status: Optional[str] = None
    # Additional fields
    cpu_cores: Optional[int] = None
    memory_gb: Optional[int] = None
    disk_gb: Optional[int] = None
    # All pc_info labels for terminals
    labels_data: Optional[Dict[str, Any]] = None


class AssetListResponse(BaseModel):
    """Asset list response with pagination."""
    total: int
    items: List[AssetResponse]


class AssetHistoryResponse(BaseModel):
    """Asset history response."""
    id: int
    asset_id: int
    action: str
    changes: Optional[Dict[str, Any]]
    operator_id: Optional[int]
    created_at: datetime


class AssetTreeNode(BaseModel):
    """Asset tree node for hierarchical display."""
    key: str
    title: str
    children: Optional[List["AssetTreeNode"]] = None
    is_leaf: bool = False
    data: Optional[Dict[str, Any]] = None


class AssetFilter(BaseModel):
    """Asset filter parameters."""
    asset_type: Optional[str] = None
    status: Optional[str] = None
    idc: Optional[str] = None
    keyword: Optional[str] = None
    label_ids: Optional[List[int]] = None
