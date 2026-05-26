"""create health_check_reports and health_check_details tables

Revision ID: 20260519_0001
Revises: 20260513_0010
Create Date: 2026-05-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0001"
down_revision: Union[str, None] = "20260513_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "health_check_reports" not in existing_tables:
        op.create_table(
            "health_check_reports",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("report_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(50), server_default="prometheus"),
            sa.Column("total_hosts", sa.Integer(), server_default="0"),
            sa.Column("ok_count", sa.Integer(), server_default="0"),
            sa.Column("warning_count", sa.Integer(), server_default="0"),
            sa.Column("critical_count", sa.Integer(), server_default="0"),
            sa.Column("notification_sent", sa.Boolean(), server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if "health_check_details" not in existing_tables:
        op.create_table(
            "health_check_details",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("report_id", sa.Integer(), sa.ForeignKey("health_check_reports.id", ondelete="CASCADE"), index=True),
            sa.Column("instance", sa.String(255), nullable=False),
            sa.Column("asset_type", sa.String(50), nullable=False),
            sa.Column("host_status", sa.String(20), nullable=False),
            sa.Column("os_info", sa.String(255), nullable=True),
            sa.Column("kernel_version", sa.String(255), nullable=True),
            sa.Column("cpu_count", sa.Integer(), nullable=True),
            sa.Column("cpu_usage", sa.Float(), nullable=True),
            sa.Column("load1", sa.Float(), nullable=True),
            sa.Column("load5", sa.Float(), nullable=True),
            sa.Column("load15", sa.Float(), nullable=True),
            sa.Column("memory_usage", sa.Float(), nullable=True),
            sa.Column("memory_total_mb", sa.Float(), nullable=True),
            sa.Column("memory_used_mb", sa.Float(), nullable=True),
            sa.Column("disk_usage", sa.Float(), nullable=True),
            sa.Column("disk_total_gb", sa.Float(), nullable=True),
            sa.Column("is_online", sa.Boolean(), server_default="true"),
            sa.Column("check_details", sa.JSON(), nullable=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    existing_indexes = [idx["name"] for idx in inspector.get_indexes("health_check_details")]
    if "ix_health_check_details_report_id" not in existing_indexes:
        op.create_index("ix_health_check_details_report_id", "health_check_details", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_health_check_details_report_id", table_name="health_check_details")
    op.drop_table("health_check_details")
    op.drop_table("health_check_reports")
