"""
Asset schemas.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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
    id: int
    created_at: datetime


class AssetBase(BaseModel):
    """Base asset schema."""
    asset_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    asset_type: str = Field(..., pattern="^(server|vm|network|storage)$")
    status: str = Field(default="active", pattern="^(active|offline|maintenance|retired)$")
    
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
    status: Optional[str] = Field(None, pattern="^(active|offline|maintenance|retired)$")
    
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
    id: int
    labels: List[LabelResponse] = []
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


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
