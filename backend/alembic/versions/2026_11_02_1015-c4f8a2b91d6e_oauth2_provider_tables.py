"""oauth2 provider tables

Revision ID: c4f8a2b91d6e
Revises: 003ccd38d5cd
Create Date: 2026-11-02

OpenTask 自建 OAuth2 授权服务器的 4 张表：client 注册、授权码、access token
登记、refresh token。详见 docs/superpowers/specs/2026-11-02-oauth2-provider-design.md。

挂在本仓唯一 PG 基线（003ccd38d5cd，ADR D11）之后，不改基线。
"""
from typing import Sequence, Union

from alembic import op
import opentask.models.base
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4f8a2b91d6e'
down_revision: Union[str, None] = '003ccd38d5cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('oauth_clients',
    sa.Column('client_id', sa.String(length=64), nullable=False, comment='客户端公开标识'),
    sa.Column('client_secret_hash', sa.String(length=64), nullable=False, comment='客户端密钥 SHA-256 哈希'),
    sa.Column('client_secret_prefix', sa.String(length=16), nullable=False, comment='客户端密钥前缀（展示用）'),
    sa.Column('name', sa.String(length=255), nullable=False, comment='应用名称'),
    sa.Column('description', sa.Text(), nullable=True, comment='应用描述'),
    sa.Column('redirect_uris', sa.Text(), nullable=False, comment='回调地址白名单（逗号分隔）'),
    sa.Column('scopes', sa.String(length=512), nullable=False, comment='允许的 scope 集合（空格分隔）'),
    sa.Column('grant_types', sa.String(length=128), nullable=False, comment='允许的授权类型（空格分隔）'),
    sa.Column('status', sa.String(length=16), nullable=False, comment='状态 ACTIVE/DISABLED'),
    sa.Column('created_by', sa.String(length=36), nullable=False, comment='注册人用户 ID'),
    sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
    sa.Column('id', opentask.models.base.CustomUUIDType(length=36), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], name=op.f('fk_oauth_clients_created_by_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth_clients'))
    )
    with op.batch_alter_table('oauth_clients', schema=None) as batch_op:
        batch_op.create_index('ix_oauth_clients_client_id', ['client_id'], unique=True)
        batch_op.create_index('ix_oauth_clients_created_by', ['created_by'], unique=False)

    op.create_table('oauth_authorization_codes',
    sa.Column('code_hash', sa.String(length=64), nullable=False, comment='授权码 SHA-256 哈希'),
    sa.Column('client_id', sa.String(length=64), nullable=False, comment='客户端标识'),
    sa.Column('user_id', sa.String(length=36), nullable=False, comment='授权用户 ID'),
    sa.Column('redirect_uri', sa.String(length=2048), nullable=False, comment='回调地址'),
    sa.Column('scope', sa.String(length=512), nullable=False, comment='授予的 scope（空格分隔）'),
    sa.Column('expires_at', sa.DateTime(), nullable=False, comment='过期时间'),
    sa.Column('used_at', sa.DateTime(), nullable=True, comment='消费时间（一次性）'),
    sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
    sa.Column('id', opentask.models.base.CustomUUIDType(length=36), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_clients.client_id'], name=op.f('fk_oauth_authorization_codes_client_id_oauth_clients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_oauth_authorization_codes_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth_authorization_codes'))
    )
    with op.batch_alter_table('oauth_authorization_codes', schema=None) as batch_op:
        batch_op.create_index('ix_oauth_authorization_codes_code_hash', ['code_hash'], unique=True)
        batch_op.create_index('ix_oauth_authorization_codes_client_id', ['client_id'], unique=False)
        batch_op.create_index('ix_oauth_authorization_codes_user_id', ['user_id'], unique=False)

    op.create_table('oauth_access_tokens',
    sa.Column('token_hash', sa.String(length=64), nullable=False, comment='access token jti 的 SHA-256 哈希'),
    sa.Column('client_id', sa.String(length=64), nullable=False, comment='客户端标识'),
    sa.Column('user_id', sa.String(length=36), nullable=False, comment='代表用户 ID'),
    sa.Column('scope', sa.String(length=512), nullable=False, comment='授予的 scope（空格分隔）'),
    sa.Column('expires_at', sa.DateTime(), nullable=False, comment='过期时间'),
    sa.Column('revoked_at', sa.DateTime(), nullable=True, comment='吊销时间'),
    sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
    sa.Column('id', opentask.models.base.CustomUUIDType(length=36), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_clients.client_id'], name=op.f('fk_oauth_access_tokens_client_id_oauth_clients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_oauth_access_tokens_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth_access_tokens'))
    )
    with op.batch_alter_table('oauth_access_tokens', schema=None) as batch_op:
        batch_op.create_index('ix_oauth_access_tokens_token_hash', ['token_hash'], unique=True)
        batch_op.create_index('ix_oauth_access_tokens_client_id', ['client_id'], unique=False)
        batch_op.create_index('ix_oauth_access_tokens_user_id', ['user_id'], unique=False)

    op.create_table('oauth_refresh_tokens',
    sa.Column('token_hash', sa.String(length=64), nullable=False, comment='refresh token SHA-256 哈希'),
    sa.Column('client_id', sa.String(length=64), nullable=False, comment='客户端标识'),
    sa.Column('user_id', sa.String(length=36), nullable=False, comment='代表用户 ID'),
    sa.Column('scope', sa.String(length=512), nullable=False, comment='授予的 scope（空格分隔）'),
    sa.Column('expires_at', sa.DateTime(), nullable=False, comment='过期时间'),
    sa.Column('revoked_at', sa.DateTime(), nullable=True, comment='吊销时间'),
    sa.Column('rotated_to_hash', sa.String(length=64), nullable=True, comment='轮换后的新 token 哈希'),
    sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
    sa.Column('id', opentask.models.base.CustomUUIDType(length=36), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_clients.client_id'], name=op.f('fk_oauth_refresh_tokens_client_id_oauth_clients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_oauth_refresh_tokens_user_id_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth_refresh_tokens'))
    )
    with op.batch_alter_table('oauth_refresh_tokens', schema=None) as batch_op:
        batch_op.create_index('ix_oauth_refresh_tokens_token_hash', ['token_hash'], unique=True)
        batch_op.create_index('ix_oauth_refresh_tokens_client_id', ['client_id'], unique=False)
        batch_op.create_index('ix_oauth_refresh_tokens_user_id', ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('oauth_refresh_tokens', schema=None) as batch_op:
        batch_op.drop_index('ix_oauth_refresh_tokens_user_id')
        batch_op.drop_index('ix_oauth_refresh_tokens_client_id')
        batch_op.drop_index('ix_oauth_refresh_tokens_token_hash')

    op.drop_table('oauth_refresh_tokens')
    with op.batch_alter_table('oauth_access_tokens', schema=None) as batch_op:
        batch_op.drop_index('ix_oauth_access_tokens_user_id')
        batch_op.drop_index('ix_oauth_access_tokens_client_id')
        batch_op.drop_index('ix_oauth_access_tokens_token_hash')

    op.drop_table('oauth_access_tokens')
    with op.batch_alter_table('oauth_authorization_codes', schema=None) as batch_op:
        batch_op.drop_index('ix_oauth_authorization_codes_user_id')
        batch_op.drop_index('ix_oauth_authorization_codes_client_id')
        batch_op.drop_index('ix_oauth_authorization_codes_code_hash')

    op.drop_table('oauth_authorization_codes')
    with op.batch_alter_table('oauth_clients', schema=None) as batch_op:
        batch_op.drop_index('ix_oauth_clients_created_by')
        batch_op.drop_index('ix_oauth_clients_client_id')

    op.drop_table('oauth_clients')
