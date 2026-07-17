"""Add audit_logs table

Revision ID: 0002_add_audit_logs
Revises: 0001_initial
Create Date: 2025-03-13 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002_add_audit_logs'
down_revision: str = '0001_initial'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create audit_logs table."""
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.String(length=50), nullable=False),
        sa.Column('operation_module', sa.String(length=50), nullable=False),
        sa.Column('object_type', sa.String(length=100), nullable=True),
        sa.Column('object_id', sa.String(length=100), nullable=True),
        sa.Column('object_name', sa.String(length=200), nullable=True),
        sa.Column('before_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('after_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('operator_id', sa.Integer(), nullable=True),
        sa.Column('operator_name', sa.String(length=100), nullable=True),
        sa.Column('operator_ip', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('operation_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_operation_type', 'audit_logs', ['operation_type'], unique=False)
    op.create_index('ix_audit_logs_operation_module', 'audit_logs', ['operation_module'], unique=False)
    op.create_index('ix_audit_logs_object_id', 'audit_logs', ['object_id'], unique=False)
    op.create_index('ix_audit_logs_operator_id', 'audit_logs', ['operator_id'], unique=False)
    op.create_index('ix_audit_logs_operation_time', 'audit_logs', ['operation_time'], unique=False)
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'], unique=False)
    op.create_index('ix_audit_logs_status', 'audit_logs', ['status'], unique=False)

    # Create composite indexes
    op.create_index('idx_audit_logs_module_time', 'audit_logs', ['operation_module', 'operation_time'], unique=False)
    op.create_index('idx_audit_logs_operator_time', 'audit_logs', ['operator_id', 'operation_time'], unique=False)
    op.create_index('idx_audit_logs_type_time', 'audit_logs', ['operation_type', 'operation_time'], unique=False)
    op.create_index('idx_audit_logs_status_time', 'audit_logs', ['status', 'operation_time'], unique=False)


def downgrade() -> None:
    """Drop audit_logs table."""
    # Drop indexes
    op.drop_index('idx_audit_logs_status_time', table_name='audit_logs')
    op.drop_index('idx_audit_logs_type_time', table_name='audit_logs')
    op.drop_index('idx_audit_logs_operator_time', table_name='audit_logs')
    op.drop_index('idx_audit_logs_module_time', table_name='audit_logs')
    op.drop_index('ix_audit_logs_status', table_name='audit_logs')
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_operation_time', table_name='audit_logs')
    op.drop_index('ix_audit_logs_operator_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_object_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_operation_module', table_name='audit_logs')
    op.drop_index('ix_audit_logs_operation_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_id', table_name='audit_logs')

    # Drop table
    op.drop_table('audit_logs')
