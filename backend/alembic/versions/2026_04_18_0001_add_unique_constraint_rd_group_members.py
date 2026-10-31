"""add unique constraint to rd_group_members

Revision ID: 2026_04_18_0001
Revises: 2026_04_18_work_mgmt
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_04_18_0001'
down_revision = '2026_04_18_work_mgmt'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the index exists before dropping
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    # Get existing indexes on rd_group_members
    try:
        indexes = inspector.get_indexes('rd_group_members')
        index_names = [idx['name'] for idx in indexes]

        # Drop old index if it exists
        if 'ix_rd_group_members_group_user' in index_names:
            op.drop_index('ix_rd_group_members_group_user', table_name='rd_group_members')

        # Create unique index
        op.create_index(
            'ix_rd_group_members_group_user',
            'rd_group_members',
            ['group_id', 'user_id'],
            unique=True
        )
    except Exception:
        # Table doesn't exist yet, skip this migration
        pass


def downgrade() -> None:
    op.drop_index('ix_rd_group_members_group_user', table_name='rd_group_members')
    op.create_index(
        'ix_rd_group_members_group_user',
        'rd_group_members',
        ['group_id', 'user_id'],
        unique=False
    )
