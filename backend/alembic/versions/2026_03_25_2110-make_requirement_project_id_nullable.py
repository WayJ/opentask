"""make requirement project_id nullable

将 requirements 表的 project_id 字段改为可空，
以支持未归类的需求

Revision ID: 202603252110
Revises: 202603251000
Create Date: 2026-03-25 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202603252110'
down_revision: Union[str, None] = '202603251000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 将 project_id 改为可空
    op.alter_column(
        'requirements',
        'project_id',
        existing_type=sa.String(36),
        nullable=True
    )


def downgrade() -> None:
    # 恢复为必填（注意：如果有未归类的需求会失败）
    op.alter_column(
        'requirements',
        'project_id',
        existing_type=sa.String(36),
        nullable=False
    )
