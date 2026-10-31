"""create access_tokens table

Revision ID: f6a7b8c9d0e1
Revises: 24634b2f3f7d
Create Date: 2026-03-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = '24634b2f3f7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'access_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, comment='用户 ID'),
        sa.Column('name', sa.String(255), nullable=False, comment='Token 名称'),
        sa.Column('description', sa.Text, nullable=True, comment='Token 描述'),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True, comment='Token SHA-256 哈希'),
        sa.Column('token_prefix', sa.String(10), nullable=False, comment='Token 前缀用于显示'),
        sa.Column('expires_at', sa.DateTime, nullable=False, comment='过期时间'),
        sa.Column('last_used_at', sa.DateTime, nullable=True, comment='最后使用时间'),
        sa.Column('created_at', sa.DateTime, nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, nullable=False, comment='更新时间'),
    )
    op.create_index('idx_access_tokens_user_id', 'access_tokens', ['user_id'])
    op.create_index('idx_access_tokens_token_hash', 'access_tokens', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_access_tokens_token_hash', table_name='access_tokens')
    op.drop_index('idx_access_tokens_user_id', table_name='access_tokens')
    op.drop_table('access_tokens')
