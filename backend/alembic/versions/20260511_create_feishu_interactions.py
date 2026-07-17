"""create feishu_interactions table

Revision ID: create_feishu_interactions
Revises: add_chat_id_receive_type
Create Date: 2026-05-11 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "create_feishu_interactions"
down_revision: str | None = "add_chat_id_receive_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feishu_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("interaction_type", sa.String(length=30), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("feishu_open_id", sa.String(length=100), nullable=True),
        sa.Column("message_id", sa.String(length=100), nullable=True),
        sa.Column("chat_id", sa.String(length=100), nullable=True),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("msg_type", sa.String(length=30), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=True),
        sa.Column("related_type", sa.String(length=50), nullable=True),
        sa.Column("related_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feishu_interactions_id"), "feishu_interactions", ["id"], unique=False)
    op.create_index(op.f("ix_feishu_interactions_direction"), "feishu_interactions", ["direction"], unique=False)
    op.create_index(op.f("ix_feishu_interactions_interaction_type"), "feishu_interactions", ["interaction_type"], unique=False)
    op.create_index(op.f("ix_feishu_interactions_user_id"), "feishu_interactions", ["user_id"], unique=False)
    op.create_index(op.f("ix_feishu_interactions_feishu_open_id"), "feishu_interactions", ["feishu_open_id"], unique=False)
    op.create_index(op.f("ix_feishu_interactions_message_id"), "feishu_interactions", ["message_id"], unique=False)
    op.create_index("idx_feishu_interactions_direction_type", "feishu_interactions", ["direction", "interaction_type"], unique=False)
    op.create_index("idx_feishu_interactions_created_at", "feishu_interactions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_feishu_interactions_created_at", table_name="feishu_interactions")
    op.drop_index("idx_feishu_interactions_direction_type", table_name="feishu_interactions")
    op.drop_index(op.f("ix_feishu_interactions_message_id"), table_name="feishu_interactions")
    op.drop_index(op.f("ix_feishu_interactions_feishu_open_id"), table_name="feishu_interactions")
    op.drop_index(op.f("ix_feishu_interactions_user_id"), table_name="feishu_interactions")
    op.drop_index(op.f("ix_feishu_interactions_interaction_type"), table_name="feishu_interactions")
    op.drop_index(op.f("ix_feishu_interactions_direction"), table_name="feishu_interactions")
    op.drop_index(op.f("ix_feishu_interactions_id"), table_name="feishu_interactions")
    op.drop_table("feishu_interactions")
