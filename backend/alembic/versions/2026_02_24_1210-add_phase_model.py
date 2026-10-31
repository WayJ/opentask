"""add phase model

添加阶段系统数据模型:
- phases 表 (阶段 - 需求和任务的中间层)
- 更新 tasks 表添加 phase_id 外键

Revision ID: 202602241210
Revises: 202602241200
Create Date: 2026-02-24 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202602241210'
down_revision: Union[str, None] = '202602241200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建阶段表
    op.create_table(
        'phases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(36), sa.ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('phase_type', sa.String(50), nullable=False, server_default='DESIGN'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('depends_on_phase_id', sa.String(36), sa.ForeignKey('phases.id', ondelete='SET NULL'), nullable=True, index=True),
    )

    # 创建索引
    op.create_index('idx_phases_requirement_id', 'phases', ['requirement_id'])
    op.create_index('idx_phases_status', 'phases', ['status'])
    op.create_index('idx_phases_order', 'phases', ['order'])
    op.create_index('idx_phases_requirement_order', 'phases', ['requirement_id', 'order'], unique=True)

    # 更新 tasks 表，添加 phase_id 外键
    # 注意：由于现有任务可能没有 phase_id，先添加可空列
    op.add_column(
        'tasks',
        sa.Column('phase_id', sa.String(36), sa.ForeignKey('phases.id', ondelete='CASCADE'), nullable=True)
    )
    op.create_index('idx_tasks_phase_id', 'tasks', ['phase_id'])

    # 更新 Requirement 模型添加 phases 关系（在 Python 代码中处理，不需要迁移）


def downgrade() -> None:
    # 删除 tasks 表的 phase_id 列和索引
    op.drop_index('idx_tasks_phase_id', 'tasks')
    op.drop_column('tasks', 'phase_id')

    # 删除 phases 表
    op.drop_table('phases')
