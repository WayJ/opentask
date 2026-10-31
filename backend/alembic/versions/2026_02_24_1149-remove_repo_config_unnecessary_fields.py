"""remove unnecessary repo config fields

移除 repo_configs 表中不再使用的字段:
- type (已不再需要)
- local_path (已不再需要)
- credentials (已不再需要)

Revision ID: 202602241149
Revises: 202602231200
Create Date: 2026-02-24 11:49:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202602241149'
down_revision: Union[str, None] = '202602231200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先删除这些列的 NOT NULL 约束
    op.alter_column('repo_configs', 'type', nullable=True)
    op.alter_column('repo_configs', 'local_path', nullable=True)

    # 删除不再使用的列
    op.drop_column('repo_configs', 'type')
    op.drop_column('repo_configs', 'local_path')
    op.drop_column('repo_configs', 'credentials')


def downgrade() -> None:
    # 恢复被删除的列
    op.add_column('repo_configs', sa.Column('credentials', sa.JSON(), nullable=True))
    op.add_column('repo_configs', sa.Column('local_path', sa.String(500), nullable=False))
    op.add_column('repo_configs', sa.Column('type', sa.String(50), nullable=False))
