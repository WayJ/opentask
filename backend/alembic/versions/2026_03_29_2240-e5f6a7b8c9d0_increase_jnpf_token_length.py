"""increase_jnpf_token_length

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-29 22:40:00.000000

增加 jnpf_token 字段长度以支持加密存储：
- 从 VARCHAR(500) 增加到 VARCHAR(1024)
- Fernet 加密后的 token 比原文长约 1/3，加上元数据，需要更大空间
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MySQL 中使用 MODIFY COLUMN 修改字段长度
    op.execute("ALTER TABLE user MODIFY COLUMN jnpf_token VARCHAR(2048) COMMENT 'JNPF 登录 token（加密存储，Fernet 格式）'")


def downgrade() -> None:
    # 回滚：恢复为 VARCHAR(500)
    op.execute("ALTER TABLE user MODIFY COLUMN jnpf_token VARCHAR(500) COMMENT 'JNPF 登录 token'")
