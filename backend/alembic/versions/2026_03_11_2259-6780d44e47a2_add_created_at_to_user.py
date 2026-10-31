"""add_created_at_to_user

Revision ID: 6780d44e47a2
Revises: b2c3d4e5f6g7
Create Date: 2026-03-11 22:59:22.770657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6780d44e47a2'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 created_at 字段到 user 表
    op.add_column('user', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'))


def downgrade() -> None:
    # 移除 created_at 字段
    op.drop_column('user', 'created_at')
