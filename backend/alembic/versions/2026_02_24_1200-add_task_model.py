"""add task model

添加任务系统数据模型:
- tasks 表 (任务)
- task_dependencies 表 (任务依赖关系)

Revision ID: 202602241200
Revises: 202602241154
Create Date: 2026-02-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202602241200'
down_revision: Union[str, None] = '202602241154'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建任务表
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(36), sa.ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=False, server_default='IMPLEMENT'),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('artifacts', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 创建任务依赖关系表
    op.create_table(
        'task_dependencies',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('depends_on_id', sa.String(36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('dependency_type', sa.String(50), nullable=False, server_default='hard'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 创建索引
    op.create_index('idx_tasks_requirement_status', 'tasks', ['requirement_id', 'status'])
    op.create_index('idx_tasks_assigned_status', 'tasks', ['assigned_to', 'status'])
    op.create_index('idx_task_dependency_unique', 'task_dependencies', ['task_id', 'depends_on_id'], unique=True)


def downgrade() -> None:
    op.drop_table('task_dependencies')
    op.drop_table('tasks')
