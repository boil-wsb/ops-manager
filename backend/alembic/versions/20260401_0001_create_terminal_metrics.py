"""Create terminal_metrics table

Revision ID: 20260401_0001
Revises:
Create Date: 2026-04-01
"""
import sqlalchemy as sa

from alembic import op

revision = "20260401_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "terminal_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("owner_username", sa.String(length=50), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("cpu_usage", sa.Float(), nullable=True),
        sa.Column("memory_usage", sa.Float(), nullable=True),
        sa.Column("disk_usage", sa.Float(), nullable=True),
        sa.Column("network_in", sa.Float(), nullable=True),
        sa.Column("network_out", sa.Float(), nullable=True),
        sa.Column("uptime_hours", sa.Integer(), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_status", sa.String(length=20), nullable=False),
        sa.Column("alert_count", sa.Integer(), nullable=False),
        sa.Column("alert_severity", sa.String(length=20), nullable=True),
        sa.Column("monitor_name", sa.String(length=100), nullable=True),
        sa.Column("metrics_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_owner_username", "terminal_metrics", ["owner_username"])
    op.create_index("idx_asset_id", "terminal_metrics", ["asset_id"])
    op.create_index("idx_current_status", "terminal_metrics", ["current_status"])
    op.create_index("idx_metrics_timestamp", "terminal_metrics", ["metrics_timestamp"])


def downgrade() -> None:
    op.drop_index("idx_metrics_timestamp", "terminal_metrics")
    op.drop_index("idx_current_status", "terminal_metrics")
    op.drop_index("idx_asset_id", "terminal_metrics")
    op.drop_index("idx_owner_username", "terminal_metrics")
    op.drop_table("terminal_metrics")
