"""add_jwt_token_fields

Revision ID: c3d4e5f6a7b8
Revises: 2b6e5bf10dac
Create Date: 2026-03-29 22:00:00.000000

添加 JWT token 管理字段，支持智能 token 复用：
- jwt_token: 存储当前有效的 JWT token
- jwt_expires_at: JWT token 过期时间（7天后）

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = '2b6e5bf10dac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 JWT token 字段
    op.add_column(
        'user',
        sa.Column('jwt_token', sa.String(500), nullable=True, comment='OpenTask 系统的 JWT token')
    )

    op.add_column(
        'user',
        sa.Column('jwt_expires_at', sa.DateTime(), nullable=True, comment='JWT token 过期时间')
    )


def downgrade() -> None:
    # 回滚：删除 JWT token 字段
    op.drop_column('user', 'jwt_expires_at')
    op.drop_column('user', 'jwt_token')
