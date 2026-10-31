"""remove_priority_and_order_from_tasks

Revision ID: 9c7e4f1a5d6c
Revises: 8a5f2d3c9e4b
Create Date: 2026-03-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c7e4f1a5d6c'
down_revision: Union[str, None] = '8a5f2d3c9e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """删除 priority 和 order 字段"""
    # 使用批量操作，因为 MySQL 在某些情况下不支持在单个语句中删除多个列
    with op.batch_alter_table('tasks') as batch_op:
        # 检查并删除 priority 列
        from sqlalchemy import inspect, text
        conn = op.get_bind()
        inspector = inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('tasks')]

        if 'priority' in columns:
            batch_op.drop_column('priority')

        if 'order' in columns:
            batch_op.drop_column('order')


def downgrade() -> None:
    """恢复 priority 和 order 字段"""
    # 恢复 priority 列
    op.add_column(
        'tasks',
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0', comment='优先级,数字越大优先级越高')
    )

    # 恢复 order 列
    op.add_column(
        'tasks',
        sa.Column('order', sa.Integer(), nullable=False, server_default='0', comment='排序，用于同级任务排序')
    )
