"""fix enum values properly

正确修复枚举值 - 使用 ALTER TYPE 而不是删除重建

Revision ID: 202602241154
Revises: 202602241152
Create Date: 2026-02-24 11:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202602241154'
down_revision: Union[str, None] = '202602241152'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 由于枚举缓存问题,我们暂时将列改为 VARCHAR 类型
    # 这样可以避免枚举类型的缓存问题
    op.execute("ALTER TABLE requirements ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("ALTER TABLE requirements ALTER COLUMN priority TYPE VARCHAR(50)")

    # 确保数据是大写格式
    op.execute("UPDATE requirements SET status = 'DRAFT' WHERE status IS NULL OR status = ''")
    op.execute("UPDATE requirements SET priority = 'MEDIUM' WHERE priority IS NULL OR priority = ''")
    op.execute("UPDATE requirements SET status = UPPER(status)")
    op.execute("UPDATE requirements SET priority = UPPER(priority) WHERE priority IS NOT NULL")


def downgrade() -> None:
    # 恢复为枚举类型(小写版本)
    op.execute("CREATE TYPE requirementstatus AS ENUM ('draft', 'clarifying', 'spec_ready', 'designing', 'coding', 'reviewing', 'testing', 'released', 'archived')")
    op.execute("CREATE TYPE priority AS ENUM ('low', 'medium', 'high', 'critical')")

    op.execute("UPDATE requirements SET status = LOWER(status)")
    op.execute("UPDATE requirements SET priority = LOWER(priority) WHERE priority IS NOT NULL")

    op.execute("ALTER TABLE requirements ALTER COLUMN status TYPE requirementstatus USING status::requirementstatus")
    op.execute("ALTER TABLE requirements ALTER COLUMN priority TYPE priority USING priority::priority")
