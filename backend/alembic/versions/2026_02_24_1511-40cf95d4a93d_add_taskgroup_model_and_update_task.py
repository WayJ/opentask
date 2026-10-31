"""add_taskgroup_model_and_update_task

Revision ID: 40cf95d4a93d
Revises: 202602241210
Create Date: 2026-02-24 15:11:21.334015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40cf95d4a93d'
down_revision: Union[str, None] = '202602241210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 task_groups 表
    op.create_table(
        'task_groups',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, comment='任务组名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='任务组描述'),
        sa.Column('order', sa.Integer(), default=0, comment='排序顺序'),
        sa.Column('requirement_id', sa.String(36), nullable=False, comment='所属需求'),
        sa.Column('status', sa.String(50), default='PENDING', nullable=False, comment='状态'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
        comment='任务组表'
    )

    # 创建索引
    op.create_index('idx_task_groups_requirement_id', 'task_groups', ['requirement_id'])

    # 更新 tasks 表，添加 task_group_id 字段
    op.add_column(
        'tasks',
        sa.Column('task_group_id', sa.String(36), nullable=True, comment='所属任务组')
    )

    # 创建外键约束
    op.create_foreign_key(
        'fk_tasks_task_group_id',
        'tasks', 'task_groups',
        ['task_group_id'], ['id'],
        ondelete='CASCADE'
    )

    # 创建索引
    op.create_index('idx_tasks_task_group_id', 'tasks', ['task_group_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_tasks_task_group_id', 'tasks')

    # 删除外键约束
    op.drop_constraint('fk_tasks_task_group_id', 'tasks', type_='foreignkey')

    # 删除 task_group_id 列
    op.drop_column('tasks', 'task_group_id')

    # 删除索引
    op.drop_index('idx_task_groups_requirement_id', 'task_groups')

    # 删除 task_groups 表
    op.drop_table('task_groups')
