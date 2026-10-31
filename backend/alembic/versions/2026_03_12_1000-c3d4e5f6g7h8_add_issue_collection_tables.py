"""add_issue_collection_tables

Revision ID: c3d4e5f6g7h8
Revises: 6780d44e47a2
Create Date: 2026-03-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = '6780d44e47a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 issue_collections 表
    op.create_table(
        'issue_collections',
        sa.Column('id', sa.String(36), primary_key=True, comment='问题集 ID (UUID)'),
        sa.Column('title', sa.String(255), nullable=False, comment='问题集标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='问题描述 (Markdown 格式)'),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', name='collection_status'), nullable=False, default='pending', comment='状态'),
        sa.Column('issue_ids', sa.JSON(), nullable=False, default='[]', comment='关联的 Issue ID 列表'),
        sa.Column('creator_id', sa.String(255), nullable=False, comment='创建人 ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        comment='问题集表'
    )

    # 创建索引
    op.create_index('idx_collection_status', 'issue_collections', ['status'])
    op.create_index('idx_collection_created_at', 'issue_collections', ['created_at'])
    op.create_index('idx_collection_creator', 'issue_collections', ['creator_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_collection_creator', 'issue_collections')
    op.drop_index('idx_collection_created_at', 'issue_collections')
    op.drop_index('idx_collection_status', 'issue_collections')

    # 删除表
    op.drop_table('issue_collections')
