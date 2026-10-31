"""add_user_ssh_keys_table

Revision ID: f2a8e9c5f1d2
Revises: add_project_id
Create Date: 2026-02-25 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a8e9c5f1d2'
down_revision: Union[str, None] = 'add_project_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 user_ssh_keys 表
    # 注意: user_id 使用 CHAR(36) 而不是 VARCHAR(36)，因为 user 表的 id 是 CHAR(36)
    op.create_table(
        'user_ssh_keys',
        sa.Column('id', sa.String(36), primary_key=True, comment='SSH 密钥 ID (UUID)'),
        sa.Column('user_id', sa.CHAR(36), nullable=False, comment='用户 ID'),
        sa.Column('name', sa.String(255), nullable=False, comment='密钥名称/备注'),
        sa.Column('public_key', sa.Text(), nullable=False, comment='SSH 公钥内容'),
        sa.Column('fingerprint', sa.String(255), nullable=False, comment='密钥指纹'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否启用'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        comment='用户 SSH 公钥表'
    )

    # 创建索引
    op.create_index('idx_user_ssh_keys_user_id', 'user_ssh_keys', ['user_id'])
    op.create_index('idx_user_ssh_keys_fingerprint', 'user_ssh_keys', ['fingerprint'])

    # 创建唯一约束 (user_id + fingerprint)
    op.create_unique_constraint('uk_user_fingerprint', 'user_ssh_keys', ['user_id', 'fingerprint'])

    # 添加外键约束
    op.create_foreign_key(
        'fk_user_ssh_keys_user_id',
        'user_ssh_keys', ['user_id'],
        'user', ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # 回滚：删除表
    op.drop_table('user_ssh_keys')
