"""
Create navigation_links table

Revision ID: 20250316_0004
Revises: 0003_add_prometheus_sync_fields
Create Date: 2026-03-16
"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0004_create_navigation_links'
down_revision: Union[str, None] = '0003_add_prometheus_sync_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create navigation_links table and role association table."""
    op.create_table(
        'navigation_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    
    op.create_index('ix_navigation_links_category', 'navigation_links', ['category'])
    
    op.create_table(
        'navigation_link_roles',
        sa.Column('navigation_link_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['navigation_link_id'], ['navigation_links.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('navigation_link_id', 'role_id'),
    )
    
    prometheus_url = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
    pushgateway_url = prometheus_url.rsplit(":", 1)[0] + ":9091"
    op.execute(f"""
        INSERT INTO navigation_links (category, name, url, icon, description, sort_order, is_active)
        VALUES 
            ('监控', '监控目标', '{prometheus_url}/targets', 'MonitorOutlined', 'Prometheus监控目标页面', 1, true),
            ('监控', 'Pushgateway', '{pushgateway_url}/#', 'CloudUploadOutlined', 'Prometheus Pushgateway', 2, true)
    """)


def downgrade() -> None:
    """Drop navigation_links and role association tables."""
    op.drop_table('navigation_link_roles')
    op.drop_index('ix_navigation_links_category', table_name='navigation_links')
    op.drop_table('navigation_links')
