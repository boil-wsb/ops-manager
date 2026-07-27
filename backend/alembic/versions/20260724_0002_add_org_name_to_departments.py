"""add org_name to departments

Revision ID: 20260724_0002
Revises: 20260724_0001_add_user_ip_bindings
Create Date: 2026-07-24 17:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260724_0002_add_org_name"
down_revision = "20260724_0001_add_user_ip_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "departments",
        sa.Column(
            "org_name",
            sa.String(length=100),
            nullable=True,
            comment="所属公司名称（根组织名）",
        ),
    )
    op.create_index(
        "ix_departments_org_name", "departments", ["org_name"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_departments_org_name", table_name="departments")
    op.drop_column("departments", "org_name")
