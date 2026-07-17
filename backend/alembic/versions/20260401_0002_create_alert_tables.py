"""Create alert tables (receivers, silences, templates, history)

Revision ID: 20260401_0002
Revises: 20260401_0001
Create Date: 2026-04-01
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260401_0002"
down_revision = "20260401_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_receivers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("webhook_url", sa.String(length=500), nullable=False),
        sa.Column("auth_type", sa.String(length=20), nullable=False, default="none"),
        sa.Column("auth_secret", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "alert_silences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("match_labels", postgresql.JSON(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("match_pattern", sa.String(length=500), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "alert_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("template_type", sa.String(length=20), nullable=False),
        sa.Column("subject_template", sa.Text(), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "alert_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alertname", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("labels", postgresql.JSON(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("annotations", postgresql.JSON(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_suppressed", sa.Boolean(), nullable=False, default=False),
        sa.Column("silence_id", sa.Integer(), nullable=True),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["silence_id"], ["alert_silences.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_alert_receivers_active", "alert_receivers", ["is_active"])
    op.create_index("idx_alert_silences_active", "alert_silences", ["is_active"])
    op.create_index("idx_alert_silences_time", "alert_silences", ["starts_at", "ends_at"])
    op.create_index("idx_alert_templates_active", "alert_templates", ["is_active"])
    op.create_index("idx_alert_templates_type", "alert_templates", ["template_type"])
    op.create_index("idx_alert_history_status", "alert_history", ["status"])
    op.create_index("idx_alert_history_alertname", "alert_history", ["alertname"])
    op.create_index("idx_alert_history_created", "alert_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_alert_history_created", "alert_history")
    op.drop_index("idx_alert_history_alertname", "alert_history")
    op.drop_index("idx_alert_history_status", "alert_history")
    op.drop_index("idx_alert_templates_type", "alert_templates")
    op.drop_index("idx_alert_templates_active", "alert_templates")
    op.drop_index("idx_alert_silences_time", "alert_silences")
    op.drop_index("idx_alert_silences_active", "alert_silences")
    op.drop_index("idx_alert_receivers_active", "alert_receivers")
    op.drop_table("alert_history")
    op.drop_table("alert_templates")
    op.drop_table("alert_silences")
    op.drop_table("alert_receivers")
