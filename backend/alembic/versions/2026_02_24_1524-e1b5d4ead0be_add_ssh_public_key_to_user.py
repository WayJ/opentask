"""add_ssh_public_key_to_user

Revision ID: e1b5d4ead0be
Revises: 40cf95d4a93d
Create Date: 2026-02-24 15:24:17.165289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1b5d4ead0be'
down_revision: Union[str, None] = '40cf95d4a93d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 ssh_public_key 字段到 user 表
    op.add_column('user', sa.Column('ssh_public_key', sa.Text(), nullable=True, comment='SSH 公钥用于 AI 助手认证'))


def downgrade() -> None:
    # 回滚：删除 ssh_public_key 字段
    op.drop_column('user', 'ssh_public_key')
