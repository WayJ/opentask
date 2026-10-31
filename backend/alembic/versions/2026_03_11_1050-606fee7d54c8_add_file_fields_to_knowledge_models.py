"""add_file_fields_to_knowledge_models

Revision ID: 606fee7d54c8
Revises: 309cee7fa646
Create Date: 2026-03-11 10:50:54.961379

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '606fee7d54c8'
down_revision: Union[str, None] = '309cee7fa646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 knowledge_bases 表添加 file_path 字段
    op.add_column('knowledge_bases', sa.Column('file_path', sa.Text(), nullable=True))

    # 为 knowledge 表添加文件优先架构字段
    op.add_column('knowledge', sa.Column('file_path', sa.Text(), nullable=True))
    op.add_column('knowledge', sa.Column('file_mtime', sa.Integer(), nullable=True))
    op.add_column('knowledge', sa.Column('last_synced_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # 回滚：删除 knowledge 表的字段
    op.drop_column('knowledge', 'last_synced_at')
    op.drop_column('knowledge', 'file_mtime')
    op.drop_column('knowledge', 'file_path')

    # 回滚：删除 knowledge_bases 表的字段
    op.drop_column('knowledge_bases', 'file_path')
