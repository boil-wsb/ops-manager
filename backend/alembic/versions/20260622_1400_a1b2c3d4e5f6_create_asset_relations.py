"""create_asset_relations

Revision ID: a1b2c3d4e5f6
Revises: 8c2905e4d6a9
Create Date: 2026-06-22 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '8c2905e4d6a9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotently create enum type (handles partial runs / create_all leftovers)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'relationtype') THEN
                CREATE TYPE relationtype AS ENUM ('CONNECTED', 'LOCATED_IN', 'CUSTOM');
            END IF;
        END
        $$;
        """
    )

    # Use postgresql.ENUM with create_type=False so SQLAlchemy won't try to
    # recreate the type during create_table (it already exists from the DO block above).
    relation_type_col = ENUM(
        'CONNECTED',
        'LOCATED_IN',
        'CUSTOM',
        name='relationtype',
        create_type=False,
    )

    op.create_table(
        'asset_relations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_asset_id', sa.Integer(), nullable=False, comment='源资产ID'),
        sa.Column('target_asset_id', sa.Integer(), nullable=False, comment='目标资产ID'),
        sa.Column(
            'relation_type',
            relation_type_col,
            nullable=False,
            server_default='CUSTOM',
            comment='关联关系类型',
        ),
        sa.Column(
            'auto_inferred',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='是否自动推断',
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
        sa.ForeignKeyConstraint(['source_asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'source_asset_id',
            'target_asset_id',
            'relation_type',
            name='uq_asset_relations_source_target_type',
        ),
        comment='资产关联关系表',
    )
    op.create_index(op.f('ix_asset_relations_id'), 'asset_relations', ['id'], unique=False)
    op.create_index(
        op.f('ix_asset_relations_source'),
        'asset_relations',
        ['source_asset_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_asset_relations_target'),
        'asset_relations',
        ['target_asset_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_asset_relations_target'), table_name='asset_relations')
    op.drop_index(op.f('ix_asset_relations_source'), table_name='asset_relations')
    op.drop_index(op.f('ix_asset_relations_id'), table_name='asset_relations')
    op.drop_table('asset_relations')
    op.execute("DROP TYPE IF EXISTS relationtype")
