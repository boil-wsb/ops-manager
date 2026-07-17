"""add_department_model_and_user_department_fk

Revision ID: 8c2905e4d6a9
Revises: 20260519_0001
Create Date: 2026-06-04 15:16:43.020938

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8c2905e4d6a9'
down_revision: str | None = '20260519_0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('departments',
    sa.Column('name', sa.String(length=200), nullable=False, comment='部门名称'),
    sa.Column('feishu_department_id', sa.String(length=100), nullable=False, comment='飞书部门ID'),
    sa.Column('parent_id', sa.Integer(), nullable=True, comment='父部门ID'),
    sa.Column('feishu_parent_department_id', sa.String(length=100), nullable=True, comment='飞书父部门ID'),
    sa.Column('is_root', sa.Boolean(), nullable=False, comment='是否根部门'),
    sa.Column('member_count', sa.Integer(), nullable=False, comment='部门成员数'),
    sa.Column('sync_at', sa.DateTime(timezone=True), nullable=True, comment='最后同步时间'),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_departments_feishu_department_id'), 'departments', ['feishu_department_id'], unique=True)
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)
    op.add_column('users', sa.Column('department_id', sa.Integer(), nullable=True, comment='所属部门ID'))
    op.create_foreign_key('fk_users_department_id', 'users', 'departments', ['department_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_users_department_id', 'users', type_='foreignkey')
    op.drop_column('users', 'department_id')
    op.drop_index(op.f('ix_departments_id'), table_name='departments')
    op.drop_index(op.f('ix_departments_feishu_department_id'), table_name='departments')
    op.drop_table('departments')
