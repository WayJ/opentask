"""fix enum case to uppercase

修复枚举值大小写问题:
- RequirementStatus 使用大写值 (DRAFT, CLARIFYING, etc.)
- Priority 使用大写值 (LOW, MEDIUM, HIGH, CRITICAL)

Revision ID: 202602241152
Revises: 202602241151
Create Date: 2026-02-24 11:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '202602241152'
down_revision: Union[str, None] = '202602241151'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除旧的枚举类型
    op.execute('DROP TYPE IF EXISTS requirementstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS priority CASCADE')

    # 重新创建大写版本的枚举
    requirementstatus_enum = postgresql.ENUM(
        'DRAFT', 'CLARIFYING', 'SPEC_READY', 'DESIGNING', 'CODING',
        'REVIEWING', 'TESTING', 'RELEASED', 'ARCHIVED',
        name='requirementstatus',
        create_type=True
    )
    requirementstatus_enum.create(op.get_bind(), checkfirst=True)

    priority_enum = postgresql.ENUM(
        'LOW', 'MEDIUM', 'HIGH', 'CRITICAL',
        name='priority',
        create_type=True
    )
    priority_enum.create(op.get_bind(), checkfirst=True)

    # 更新现有数据为大写
    op.execute("UPDATE requirements SET status = UPPER(status)")
    op.execute("UPDATE requirements SET priority = UPPER(priority) WHERE priority IS NOT NULL")


def downgrade() -> None:
    # 恢复小写枚举
    op.execute('DROP TYPE IF EXISTS requirementstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS priority CASCADE')

    requirementstatus_enum = postgresql.ENUM(
        'draft', 'clarifying', 'spec_ready', 'designing', 'coding',
        'reviewing', 'testing', 'released', 'archived',
        name='requirementstatus',
        create_type=True
    )
    requirementstatus_enum.create(op.get_bind(), checkfirst=True)

    priority_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'critical',
        name='priority',
        create_type=True
    )
    priority_enum.create(op.get_bind(), checkfirst=True)

    # 更新数据为小写
    op.execute("UPDATE requirements SET status = LOWER(status)")
    op.execute("UPDATE requirements SET priority = LOWER(priority) WHERE priority IS NOT NULL")
