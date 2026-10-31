"""add requirement enums

添加需求和优先级枚举类型:
- RequirementStatus (draft, clarifying, spec_ready, designing, coding, reviewing, testing, released, archived)
- Priority (low, medium, high, critical)

Revision ID: 202602241151
Revises: 202602241149
Create Date: 2026-02-24 11:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '202602241151'
down_revision: Union[str, None] = '202602241149'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 RequirementStatus 枚举类型
    requirementstatus_enum = postgresql.ENUM(
        'draft', 'clarifying', 'spec_ready', 'designing', 'coding',
        'reviewing', 'testing', 'released', 'archived',
        name='requirementstatus',
        create_type=True
    )
    requirementstatus_enum.create(op.get_bind(), checkfirst=True)

    # 创建 Priority 枚举类型
    priority_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'critical',
        name='priority',
        create_type=True
    )
    priority_enum.create(op.get_bind(), checkfirst=True)

    # 修改 requirements 表的列类型以使用枚举
    # 先备份数据
    op.execute("ALTER TABLE requirements RENAME COLUMN status TO status_old")
    op.execute("ALTER TABLE requirements RENAME COLUMN priority TO priority_old")

    # 添加新的枚举列
    op.add_column('requirements', sa.Column('status', sa.String(50), nullable=False, server_default='draft'))
    op.add_column('requirements', sa.Column('priority', sa.String(50), nullable=True))

    # 迁移数据
    op.execute("UPDATE requirements SET status = LOWER(status_old)")
    op.execute("UPDATE requirements SET priority = COALESCE(LOWER(priority_old), 'medium')")

    # 删除旧列
    op.drop_column('requirements', 'status_old')
    op.drop_column('requirements', 'priority_old')


def downgrade() -> None:
    # 恢复原来的列结构
    op.add_column('requirements', sa.Column('status_old', sa.VARCHAR(50), nullable=False))
    op.add_column('requirements', sa.Column('priority_old', sa.VARCHAR(50), nullable=True))

    # 迁移数据回来
    op.execute("UPDATE requirements SET status_old = UPPER(status)")
    op.execute("UPDATE requirements SET priority_old = UPPER(priority)")

    # 删除枚举列
    op.drop_column('requirements', 'status')
    op.drop_column('requirements', 'priority')

    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS requirementstatus')
    op.execute('DROP TYPE IF EXISTS priority')
