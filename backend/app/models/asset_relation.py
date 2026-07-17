"""
Asset relation models.
"""

import enum

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class RelationType(enum.StrEnum):
    """Asset relation type enum."""

    CONNECTED = "CONNECTED"  # 网络连接（同网段自动推断）
    LOCATED_IN = "LOCATED_IN"  # 同位置（同 IDC 自动推断）
    CUSTOM = "CUSTOM"  # 用户自定义（手动拖拽连线）


class AssetRelation(BaseModel):
    """Asset relation model for storing relationships between assets."""

    __tablename__ = "asset_relations"

    source_asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[RelationType] = mapped_column(
        SQLEnum(RelationType),
        default=RelationType.CUSTOM,
        nullable=False,
    )
    auto_inferred: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    source_asset: Mapped["Asset"] = relationship(
        "Asset",
        foreign_keys=[source_asset_id],
        back_populates="outgoing_relations",
        lazy="selectin",
    )
    target_asset: Mapped["Asset"] = relationship(
        "Asset",
        foreign_keys=[target_asset_id],
        back_populates="incoming_relations",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "relation_type",
            name="uq_asset_relations_source_target_type",
        ),
        Index("ix_asset_relations_source", "source_asset_id"),
        Index("ix_asset_relations_target", "target_asset_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AssetRelation {self.source_asset_id}->{self.target_asset_id} "
            f"({self.relation_type})>"
        )
