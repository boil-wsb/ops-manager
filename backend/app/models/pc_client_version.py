"""
PC Client version management model.
"""
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PCClientVersion(BaseModel):
    """PC Client version model for managing updates."""

    __tablename__ = "pc_client_versions"

    version: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    force_update: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
