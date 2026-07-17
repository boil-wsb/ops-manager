"""
Asset relation schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssetRelationCreate(BaseModel):
    """Schema for creating a manual asset relation."""

    source_asset_id: int = Field(..., description="源资产ID")
    target_asset_id: int = Field(..., description="目标资产ID")
    relation_type: str = Field(
        default="CUSTOM",
        pattern="^(CONNECTED|LOCATED_IN|CUSTOM)$",
        description="关联关系类型",
    )


class AssetRelationOut(BaseModel):
    """Schema for asset relation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str = Field(..., description="源资产ID(字符串)")
    target: str = Field(..., description="目标资产ID(字符串)")
    relation_type: str
    auto_inferred: bool


class TopologyMetrics(BaseModel):
    """Resource metrics for a topology node (sourced from daily health check)."""

    cpu: float | None = Field(None, description="CPU使用率(%)")
    mem: float | None = Field(None, description="内存使用率(%)")
    disk: float | None = Field(None, description="磁盘使用率(%)")
    load1: float | None = Field(None, description="1分钟负载")
    memory_total_mb: float | None = Field(None, description="内存总量(MB)")
    disk_total_gb: float | None = Field(None, description="磁盘总量(GB)")
    host_status: str | None = Field(None, description="巡检状态 ok/warning/critical")
    checked_at: datetime | None = Field(None, description="巡检时间")


class TopologyLabel(BaseModel):
    """Label attached to a topology node."""

    id: int
    name: str
    color: str


class TopologyNode(BaseModel):
    """Topology node schema."""

    id: str = Field(..., description="节点ID(资产ID字符串)")
    name: str
    type: str = Field(..., description="资产类型 SERVER/VM/NETWORK/STORAGE/TERMINAL")
    status: str
    ip_address: str | None = None
    idc: str | None = None
    owner_name: str | None = None
    os_type: str | None = None
    os_version: str | None = None
    cpu_cores: int | None = None
    memory_gb: int | None = None
    disk_gb: int | None = None
    labels: list[TopologyLabel] = Field(default_factory=list, description="资产标签")
    metrics: TopologyMetrics = Field(default_factory=TopologyMetrics)


class TopologyEdge(BaseModel):
    """Topology edge schema.

    Edges are fully auto-inferred (no manual relations):
    - same label -> CONNECTED, label field carries the label name
    - same IDC -> LOCATED_IN
    - same /24 subnet -> CONNECTED
    """

    id: str
    source: str
    target: str
    relation_type: str
    auto_inferred: bool
    label: str | None = Field(None, description="同标签关联的标签名")
    label_color: str | None = Field(None, description="标签颜色")


class TopologyGroup(BaseModel):
    """Topology group summary schema."""

    type: str
    count: int


class TopologyResponse(BaseModel):
    """Topology data response containing nodes, edges and group summaries."""

    nodes: list[TopologyNode]
    edges: list[TopologyEdge]
    groups: list[TopologyGroup]


class AssetRelationDeleteResponse(BaseModel):
    """Response schema for relation deletion."""

    success: bool
