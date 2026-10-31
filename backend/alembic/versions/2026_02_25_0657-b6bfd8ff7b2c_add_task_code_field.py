"""add_task_code_field

Revision ID: b6bfd8ff7b2c
Revises: f2a8e9c5f1d2
Create Date: 2026-02-25 06:57:40.165333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6bfd8ff7b2c'
down_revision: Union[str, None] = 'f2a8e9c5f1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 检查并添加 code 字段
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tasks')]

    if 'code' not in columns:
        op.add_column('tasks', sa.Column('code', sa.String(50), nullable=True, comment='任务编码 (如 1, 1.1, 2.1)'))

    # 检查并创建索引
    indexes = inspector.get_indexes('tasks')
    if not any(idx['name'] == 'idx_tasks_code' for idx in indexes):
        op.create_index('idx_tasks_code', 'tasks', ['code'])

    if not any(idx['name'] == 'idx_tasks_requirement_code' for idx in indexes):
        op.create_index('idx_tasks_requirement_code', 'tasks', ['requirement_id', 'code'])


def downgrade() -> None:
    # 删除索引
    try:
        op.drop_index('idx_tasks_code', table_name='tasks')
    except Exception:
        pass

    try:
        op.drop_index('idx_tasks_requirement_code', table_name='tasks')
    except Exception:
        pass

    # 删除字段
    op.drop_column('tasks', 'code')
