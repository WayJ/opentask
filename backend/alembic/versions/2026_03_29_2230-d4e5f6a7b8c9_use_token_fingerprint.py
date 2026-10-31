"""use_token_fingerprint

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-29 22:30:00.000000

安全改进：
1. 删除明文 jwt_token 字段，改用 jwt_token_fingerprint（SHA-256 哈希）
2. jnpf_token 字段保持不变，但存储内容改为加密后的 token

注意事项：
- 现有的 JWT token 将失效，用户需要重新登录
- 现有的 JNPF token 将被加密存储
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除明文 jwt_token 字段
    op.drop_column('user', 'jwt_token')

    # 2. 添加 jwt_token_fingerprint 字段（SHA-256 哈希，固定 64 字符）
    op.add_column(
        'user',
        sa.Column('jwt_token_fingerprint', sa.String(64), nullable=True, comment='JWT token 的 SHA-256 哈希（用于验证但不泄露token）')
    )

    # 3. jnpf_token 字段保持不变，但应用程序会加密存储内容
    # 注意：现有的 JNPF token 将在下次登录时重新加密


def downgrade() -> None:
    # 回滚：恢复明文存储（不推荐）

    # 1. 删除 token 指纹字段
    op.drop_column('user', 'jwt_token_fingerprint')

    # 2. 恢复明文 jwt_token 字段
    op.add_column(
        'user',
        sa.Column('jwt_token', sa.String(500), nullable=True, comment='OpenTask 系统的 JWT token')
    )
