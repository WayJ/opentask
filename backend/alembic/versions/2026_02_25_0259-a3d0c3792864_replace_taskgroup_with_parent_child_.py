"""replace_taskgroup_with_parent_child_tasks

Revision ID: a3d0c3792864
Revises: e1b5d4ead0be
Create Date: 2026-02-25 02:59:07.690560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d0c3792864'
down_revision: Union[str, None] = 'e1b5d4ead0be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 先删除 tasks 表中的 task_group_id 外键约束
    op.drop_constraint('fk_tasks_task_group_id_tasks', 'tasks', type_='foreignkey', if_exists=True)
    op.drop_index('idx_tasks_task_group_id', table_name='tasks', if_exists=True)
    op.drop_column('tasks', 'task_group_id', if_exists=True)

    # 2. 删除 task_groups 表
    op.drop_table('task_groups', if_exists=True)

    # 3. 添加 parent_id 列到 tasks 表，支持父子任务关系
    op.add_column('tasks', sa.Column('parent_id', sa.String(36), nullable=True, comment='父任务ID，支持最多两级任务'))
    op.add_column('tasks', sa.Column('order', sa.Integer(), nullable=False, server_default='0', comment='同级任务排序'))

    # 4. 创建外键和索引
    op.create_foreign_key(
        'fk_tasks_parent_id',
        'tasks', 'tasks',
        ['parent_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_tasks_parent_id', 'tasks', ['parent_id'])


def downgrade() -> None:
    # 回滚
    op.drop_index('idx_tasks_parent_id', table_name='tasks')
    op.drop_constraint('fk_tasks_parent_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'order')
    op.drop_column('tasks', 'parent_id')

    # 恢复 task_group_id
    op.add_column('tasks', sa.Column('task_group_id', sa.String(36), nullable=True))
    op.create_index('idx_tasks_task_group_id', 'tasks', ['task_group_id'])

    # 恢复 task_groups 表
    op.create_table(
        'task_groups',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('requirement_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(50), default='PENDING'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE')
    )

    # 恢复外键
    op.create_foreign_key(
        'fk_tasks_task_group_id_tasks',
        'tasks', 'task_groups',
        ['task_group_id'], ['id'],
        ondelete='CASCADE'
    )
