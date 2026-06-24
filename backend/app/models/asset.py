"""
Asset models.
"""

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tz import now_shanghai
from app.models.base import BaseModel


class AssetType(enum.StrEnum):
    """Asset type enum."""

    SERVER = "SERVER"
    VM = "VM"
    NETWORK = "NETWORK"
    STORAGE = "STORAGE"
    TERMINAL = "TERMINAL"


class AssetStatus(enum.StrEnum):
    """Asset status enum."""

    ACTIVE = "ACTIVE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class AssetSource(enum.StrEnum):
    """Asset source enum."""

    MANUAL = "MANUAL"
    PROMETHEUS = "PROMETHEUS"
    IMPORTED = "IMPORTED"


class SyncStatus(enum.StrEnum):
    """Sync status enum."""

    PENDING = "PENDING"
    SYNCED = "SYNCED"
    ERROR = "ERROR"


# Asset-Label association table
asset_labels = Table(
    "asset_labels",
    BaseModel.metadata,
    Column("asset_id", Integer, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", Integer, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=now_shanghai),
)


class Label(BaseModel):
    """Label model for tagging assets."""

    __tablename__ = "labels"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#1890ff", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", secondary=asset_labels, back_populates="labels", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Label {self.name}>"


class Asset(BaseModel):
    """Asset model for managing IT assets."""

    __tablename__ = "assets"

    # Basic info
    asset_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(
        SQLEnum(AssetStatus), default=AssetStatus.ACTIVE, nullable=False
    )

    # Network info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    private_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)

    # Hardware info
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    os_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    arch: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Terminal specific info (from pc_info metrics)
    hostname: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uuid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Prometheus sync info
    source: Mapped[str] = mapped_column(
        String(50), default=AssetSource.MANUAL.value, nullable=False
    )
    prometheus_instance: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(
        String(50), default=SyncStatus.PENDING.value, nullable=False
    )

    # Location info
    idc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rack: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata
    labels_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    owner: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    labels: Mapped[list["Label"]] = relationship(
        "Label", secondary=asset_labels, back_populates="assets", lazy="selectin"
    )
    terminal_metrics: Mapped[list["TerminalMetric"]] = relationship(
        "TerminalMetric", back_populates="asset", lazy="selectin"
    )
    # Asset topology relations (asset_relations table)
    # Use lazy="select" (default lazy loading) so ordinary Asset list queries
    # are NOT forced to join asset_relations. Topology endpoint queries the
    # relation table directly via crud_asset_relation, so these relationships
    # are only populated on explicit access.
    outgoing_relations: Mapped[list["AssetRelation"]] = relationship(
        "AssetRelation",
        foreign_keys="AssetRelation.source_asset_id",
        back_populates="source_asset",
        cascade="all, delete-orphan",
        lazy="select",
    )
    incoming_relations: Mapped[list["AssetRelation"]] = relationship(
        "AssetRelation",
        foreign_keys="AssetRelation.target_asset_id",
        back_populates="target_asset",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Indexes
    __table_args__ = (
        Index("ix_assets_status", "status"),
        Index("ix_assets_type", "asset_type"),
        Index("ix_assets_idc", "idc"),
    )

    def __repr__(self) -> str:
        return f"<Asset {self.asset_id}: {self.name}>"


class AssetHistory(BaseModel):
    """Asset history for tracking changes."""

    __tablename__ = "asset_history"

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, update, delete
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    operator: Mapped[Optional["User"]] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AssetHistory {self.asset_id}: {self.action}>"
