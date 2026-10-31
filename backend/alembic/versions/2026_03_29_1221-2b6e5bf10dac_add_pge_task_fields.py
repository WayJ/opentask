"""add_pge_task_fields

Revision ID: 2b6e5bf10dac
Revises: 2026_03_27_2329
Create Date: 2026-03-29 12:21:28.661399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b6e5bf10dac'
down_revision: Union[str, None] = '2026_03_27_2329'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 framework 字段到 tasks 表
    op.add_column(
        'tasks',
        sa.Column(
            'framework',
            sa.String(50),
            nullable=True,
            index=True,
            comment='任务框架（如 PGE）'
        )
    )

    # 添加 required_skills 字段到 tasks 表
    op.add_column(
        'tasks',
        sa.Column(
            'required_skills',
            sa.JSON(),
            nullable=True,
            comment='必需的 Superpower Skills'
        )
    )


def downgrade() -> None:
    # 删除 required_skills 字段
    op.drop_column('tasks', 'required_skills')

    # 删除 framework 字段
    op.drop_column('tasks', 'framework')
