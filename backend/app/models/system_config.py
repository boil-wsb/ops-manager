from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SystemConfig(BaseModel):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    group: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_system_configs_group", "group"),
    )

    def __repr__(self) -> str:
        return f"<SystemConfig {self.group}.{self.key}>"
