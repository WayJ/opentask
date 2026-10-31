"""add_jnpf_integration_fields

Revision ID: a1b2c3d4e5f6
Revises: 9a1e0e9ca547
Create Date: 2026-03-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9a1e0e9ca547'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== JNPF 集成字段 =====

    # 添加 jnpf_user_id（唯一索引）
    op.add_column(
        'user',
        sa.Column('jnpf_user_id', sa.String(100), nullable=True, comment='JNPF 用户 ID（唯一索引，用于关联 JNPF 用户）')
    )
    op.create_unique_constraint('uq_user_jnpf_user_id', 'user', ['jnpf_user_id'])

    # 添加其他 JNPF 字段
    op.add_column('user', sa.Column('jnpf_account', sa.String(100), nullable=True, comment='JNPF 账号'))
    op.add_column('user', sa.Column('jnpf_name', sa.String(100), nullable=True, comment='JNPF 姓名'))
    op.add_column('user', sa.Column('organize_id', sa.String(100), nullable=True, comment='JNPF 组织 ID'))
    op.add_column('user', sa.Column('organize_name', sa.String(200), nullable=True, comment='JNPF 组织名称'))
    op.add_column('user', sa.Column('position_id', sa.String(100), nullable=True, comment='JNPF 岗位 ID'))
    op.add_column('user', sa.Column('position_name', sa.String(100), nullable=True, comment='JNPF 岗位名称'))

    # ===== 本地权限管理字段 =====
    op.add_column('user', sa.Column('status', sa.Integer(), server_default='1', comment='用户状态：1-启用、0-禁用'))
    op.add_column('user', sa.Column('role', sa.String(50), server_default='viewer', comment='用户角色：admin、maintainer、developer、viewer'))

    # ===== 时间字段 =====
    op.add_column('user', sa.Column('last_login_time', sa.DateTime(), nullable=True, comment='最后登录时间'))
    op.add_column('user', sa.Column('sync_time', sa.DateTime(), nullable=True, comment='JNPF 信息同步时间'))

    # ===== 修改原有字段为可空（兼容 JNPF 用户）=====
    # MySQL 中修改字段为可空
    op.execute("ALTER TABLE user MODIFY COLUMN name VARCHAR(100) NULL COMMENT '用户名（保留兼容）'")
    op.execute("ALTER TABLE user MODIFY COLUMN password VARCHAR(255) NULL COMMENT '密码（JNPF 用户不需要）'")


def downgrade() -> None:
    # 回滚：删除所有新增字段

    # 删除时间字段
    op.drop_column('user', 'sync_time')
    op.drop_column('user', 'last_login_time')

    # 删除权限管理字段
    op.drop_column('user', 'role')
    op.drop_column('user', 'status')

    # 删除 JNPF 字段
    op.drop_column('user', 'position_name')
    op.drop_column('user', 'position_id')
    op.drop_column('user', 'organize_name')
    op.drop_column('user', 'organize_id')
    op.drop_column('user', 'jnpf_name')
    op.drop_column('user', 'jnpf_account')
    op.drop_constraint('uq_user_jnpf_user_id', 'user', type_='unique')
    op.drop_column('user', 'jnpf_user_id')

    # 恢复原有字段为 NOT NULL
    op.execute("ALTER TABLE user MODIFY COLUMN name VARCHAR(100) NOT NULL")
    op.execute("ALTER TABLE user MODIFY COLUMN password VARCHAR(255) NOT NULL")
