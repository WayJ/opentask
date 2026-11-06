"""oauth2 install flow table

Revision ID: h1b2c3d4e5f6
Revises: g0a1b2c3d4e5
Create Date: 2026-11-06

OAuth 自动接入（Install Flow）安装申请表：一次性 PKCE verifier 换来的 client 登记申请。
协议见 docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md。

安全口径：
- 无长期凭据：只存 code_challenge（= BASE64URL(SHA256(verifier))）；
- 安装码只存 SHA-256 哈希；client_secret 仍由 oauth_clients 按既有口径存哈希。
"""

from typing import Sequence, Union

from alembic import op
import opentask.models.base
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'h1b2c3d4e5f6'
down_revision: Union[str, None] = 'g0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'oauth_install_requests',
        sa.Column('client_id', sa.String(length=64), nullable=False, comment='客户端公开标识'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='应用名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='应用描述'),
        sa.Column('redirect_uris', sa.Text(), nullable=False, comment='回调地址白名单（逗号分隔）'),
        sa.Column('scopes', sa.String(length=512), nullable=False, comment='允许的 scope 集合（空格分隔）'),
        sa.Column('grant_types', sa.String(length=128), nullable=False, comment='允许的授权类型（空格分隔）'),
        sa.Column('callback_url', sa.String(length=2048), nullable=False, comment='安装完成回跳地址'),
        sa.Column('state', sa.String(length=256), nullable=True, comment='申请方 state（原样回传）'),
        sa.Column('code_challenge', sa.String(length=128), nullable=False, comment='PKCE S256 challenge'),
        sa.Column('code_challenge_method', sa.String(length=16), nullable=False, comment='PKCE 方法（固定 S256）'),
        sa.Column('status', sa.String(length=16), nullable=False, comment='申请状态'),
        sa.Column('code_hash', sa.String(length=64), nullable=True, comment='安装码 SHA-256 哈希'),
        sa.Column('code_expires_at', sa.DateTime(), nullable=True, comment='安装码过期时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='申请过期时间'),
        sa.Column('approved_by', sa.String(length=36), nullable=True, comment='批准人用户 ID'),
        sa.Column('approved_at', sa.DateTime(), nullable=True, comment='批准时间'),
        sa.Column('rejected_at', sa.DateTime(), nullable=True, comment='拒绝时间'),
        sa.Column('first_exchange_at', sa.DateTime(), nullable=True, comment='首次兑换时间'),
        sa.Column('consumed_at', sa.DateTime(), nullable=True, comment='兑换时间'),
        sa.Column('recovery_count', sa.Integer(), nullable=False, comment='恢复兑换次数'),
        sa.Column('recovery_used_at', sa.DateTime(), nullable=True, comment='最近一次恢复兑换时间'),
        sa.Column('request_ip', sa.String(length=64), nullable=True, comment='申请来源 IP'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='申请来源 User-Agent'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('id', opentask.models.base.CustomUUIDType(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ['approved_by'],
            ['user.id'],
            name=op.f('fk_oauth_install_requests_approved_by_user'),
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth_install_requests')),
    )
    with op.batch_alter_table('oauth_install_requests', schema=None) as batch_op:
        batch_op.create_index('ix_oauth_install_requests_status_expires_at', ['status', 'expires_at'], unique=False)
        batch_op.create_index('ix_oauth_install_requests_client_id_status', ['client_id', 'status'], unique=False)
        batch_op.create_index('ix_oauth_install_requests_code_hash', ['code_hash'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('oauth_install_requests', schema=None) as batch_op:
        batch_op.drop_index('ix_oauth_install_requests_code_hash')
        batch_op.drop_index('ix_oauth_install_requests_client_id_status')
        batch_op.drop_index('ix_oauth_install_requests_status_expires_at')

    op.drop_table('oauth_install_requests')
