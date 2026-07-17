"""create_suggestion_tables

Revision ID: c1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-14 00:01:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c1a2b3c4d5e6'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 给 departments 表添加 leader_id 列
    op.add_column(
        'departments',
        sa.Column('leader_id', sa.Integer(), nullable=True, comment='部门负责人')
    )
    op.create_foreign_key(
        'fk_departments_leader_id',
        'departments',
        'users',
        ['leader_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # 2. 创建 suggestions 表
    op.create_table(
        'suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, comment='意见内容'),
        sa.Column('highlights', sa.Text(), nullable=True, comment='项目服务亮点'),
        sa.Column('innovation_ideas', sa.Text(), nullable=True, comment='创新/团队协助效能提高idea'),
        sa.Column(
            'status', sa.String(length=20), nullable=False,
            server_default='pending', comment='状态'
        ),
        sa.Column('query_code', sa.String(length=6), nullable=False, comment='匿名查询码'),
        sa.Column('submitter_id', sa.Integer(), nullable=True, comment='提交者ID(审计用,不展示)'),
        sa.Column('client_ip', sa.String(length=45), nullable=True, comment='提交IP'),
        sa.Column('market_result', sa.Text(), nullable=True, comment='市场部执行结果'),
        sa.Column('market_reviewer_id', sa.Integer(), nullable=True, comment='市场部存档人'),
        sa.Column(
            'archived_at', sa.DateTime(timezone=True), nullable=True, comment='存档时间'
        ),
        sa.Column('reject_reason', sa.Text(), nullable=True, comment='驳回原因'),
        sa.Column('rejected_by', sa.Integer(), nullable=True, comment='驳回人'),
        sa.Column(
            'rejected_at', sa.DateTime(timezone=True), nullable=True, comment='驳回时间'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['submitter_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['market_reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('query_code', name='uq_suggestions_query_code'),
        comment='匿名建议表',
    )
    op.create_index(op.f('ix_suggestions_id'), 'suggestions', ['id'], unique=False)
    op.create_index(op.f('ix_suggestions_status'), 'suggestions', ['status'], unique=False)
    op.create_index(op.f('ix_suggestions_query_code'), 'suggestions', ['query_code'], unique=True)

    # 3. 创建 suggestion_assignments 表
    op.create_table(
        'suggestion_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suggestion_id', sa.Integer(), nullable=False, comment='建议ID'),
        sa.Column('department_id', sa.Integer(), nullable=True, comment='指派部门'),
        sa.Column('assignee_user_id', sa.Integer(), nullable=True, comment='指派人'),
        sa.Column('assignee_open_id', sa.String(length=64), nullable=True, comment='指派人飞书open_id'),
        sa.Column('open_message_id', sa.String(length=100), nullable=True, comment='飞书卡片消息ID'),
        sa.Column(
            'status', sa.String(length=20), nullable=False,
            server_default='pending', comment='pending/approved/rejected'
        ),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True, comment='审批时间'),
        sa.Column('review_comment', sa.Text(), nullable=True, comment='审批意见'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['suggestion_id'], ['suggestions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assignee_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='建议指派关系表',
    )
    op.create_index(
        op.f('ix_suggestion_assignments_id'), 'suggestion_assignments', ['id'], unique=False
    )
    op.create_index(
        op.f('ix_suggestion_assignments_suggestion_id'),
        'suggestion_assignments',
        ['suggestion_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_suggestion_assignments_open_message_id'),
        'suggestion_assignments',
        ['open_message_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_suggestion_assignments_open_message_id'),
        table_name='suggestion_assignments',
    )
    op.drop_index(
        op.f('ix_suggestion_assignments_suggestion_id'),
        table_name='suggestion_assignments',
    )
    op.drop_index(op.f('ix_suggestion_assignments_id'), table_name='suggestion_assignments')
    op.drop_table('suggestion_assignments')
    op.drop_index(op.f('ix_suggestions_query_code'), table_name='suggestions')
    op.drop_index(op.f('ix_suggestions_status'), table_name='suggestions')
    op.drop_index(op.f('ix_suggestions_id'), table_name='suggestions')
    op.drop_table('suggestions')
    op.drop_constraint('fk_departments_leader_id', 'departments', type_='foreignkey')
    op.drop_column('departments', 'leader_id')
