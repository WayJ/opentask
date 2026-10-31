"""add_agent_task_link

Revision ID: 24634b2f3f7d
Revises: e5f6a7b8c9d0
Create Date: 2026-03-30 14:14:01.426135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24634b2f3f7d'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 agent_task_id 字段到 tasks 表
    op.add_column(
        'tasks',
        sa.Column(
            'agent_task_id',
            sa.String(36),
            nullable=True,
            index=True,
            comment='关联的 Mission Center 任务 ID'
        )
    )

    # 添加复合索引以优化查询
    op.create_index(
        'idx_tasks_requirement_agent_task',
        'tasks',
        ['requirement_id', 'agent_task_id']
    )

    # 注意：外键约束暂时不添加，避免依赖问题
    # 后续可以在确认 agent_tasks 表存在后再添加


def downgrade() -> None:
    # 删除复合索引
    op.drop_index('idx_tasks_requirement_agent_task', table_name='tasks')

    # 删除 agent_task_id 字段
    op.drop_column('tasks', 'agent_task_id')
