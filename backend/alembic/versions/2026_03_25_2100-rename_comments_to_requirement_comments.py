"""rename comments table to requirement_comments

将需求评论表从 comments 重命名为 requirement_comments,
以区分需求评论和 Issue 评论

Revision ID: 202603251000
Revises: 202603040800
Create Date: 2026-03-25 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202603251000'
down_revision: Union[str, None] = '2026_03_16_1850'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 检查表是否存在，如果存在则重命名
    # 使用 batch_alter_table 来安全地处理可能不存在的情况
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if 'comments' in tables:
        op.rename_table('comments', 'requirement_comments')
    # MySQL 不支持直接重命名索引，需要删除并重新创建
    # 由于表已经重命名，索引会自动跟随表名变化，不需要手动处理


def downgrade() -> None:
    # 恢复表名
    op.rename_table('requirement_comments', 'comments')

    # 索引会自动恢复，不需要手动处理
