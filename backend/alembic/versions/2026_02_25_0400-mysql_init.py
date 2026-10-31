"""mysql init

MySQL 数据库初始化迁移，创建核心数据表

Revision ID: 202602250400
Revises: 
Create Date: 2026-02-25 04:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202602250400'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建需求表
    op.create_table(
        'requirements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='draft'),
        sa.Column('priority', sa.String(50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('assignee_id', sa.String(255), nullable=True, index=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4'
    )
    op.create_index('idx_requirements_status', 'requirements', ['status'])
    op.create_index('idx_requirements_priority', 'requirements', ['priority'])
    op.create_index('idx_requirements_created_at', 'requirements', ['created_at'])

    # 创建项目表
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4'
    )

    # 创建任务表
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(36), nullable=False, index=True),
        sa.Column('parent_id', sa.String(36), nullable=True, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='PENDING'),
        sa.Column('priority', sa.Integer(), nullable=False, default=50),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('artifacts', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Column('order', sa.Integer(), nullable=False, default=0),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4'
    )
    op.create_index('idx_tasks_requirement_id', 'tasks', ['requirement_id'])
    op.create_index('idx_tasks_status', 'tasks', ['status'])

    # 创建事件表
    op.create_table(
        'events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(36), nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False, index=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('actor', sa.String(255), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('snapshot', sa.JSON(), nullable=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4'
    )

    # 创建需求编码序列表
    op.create_table(
        'requirement_code_sequence',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('year', sa.Integer, nullable=False, unique=True, index=True),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4'
    )


def downgrade() -> None:
    op.drop_table('requirement_code_sequence')
    op.drop_table('events')
    op.drop_table('tasks')
    op.drop_table('projects')
    op.drop_table('requirements')
