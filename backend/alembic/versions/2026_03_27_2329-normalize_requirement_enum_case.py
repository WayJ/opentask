"""normalize requirement enum case to lowercase

统一需求模块枚举值大小写为小写:
- RequirementStatus 使用小写值 (draft, clarifying, etc.)
- Priority 使用小写值 (low, medium, high, critical)

这样与 Issue 模块保持一致，符合现代 API 设计规范。

注意：MySQL 使用 VARCHAR 存储枚举值，不是 ENUM 类型

Revision ID: 2026_03_27_2329
Revises: 2026_03_26_1107
Create Date: 2026-03-27 23:29:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_03_27_2329'
down_revision: Union[str, None] = '2026_03_26_1107'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 更新现有数据为小写
    op.execute("UPDATE requirements SET status = LOWER(status)")
    op.execute("UPDATE requirements SET priority = LOWER(priority) WHERE priority IS NOT NULL")


def downgrade() -> None:
    # 恢复大写枚举
    op.execute("UPDATE requirements SET status = UPPER(status)")
    op.execute("UPDATE requirements SET priority = UPPER(priority) WHERE priority IS NOT NULL")
