"""add_issue_code_field

Revision ID: 309cee7fa646
Revises: 2026_03_10_1203
Create Date: 2026-03-10 22:54:47.180540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '309cee7fa646'
down_revision: Union[str, None] = '2026_03_10_1203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 issue_code 字段到 issues 表（允许 NULL）
    op.add_column(
        'issues',
        sa.Column('issue_code', sa.String(50), nullable=True, comment='问题编号')
    )

    # 为现有数据生成 issue_code
    # 使用用户变量来计算序号，避免 MySQL 的子查询限制
    op.execute("""
        UPDATE issues i1
        INNER JOIN (
            SELECT
                id,
                CONCAT('ISSUE', YEAR(created_at), '-', @row_number:=IF(@prev_year=YEAR(created_at), @row_number+1, 1)) as issue_code,
                @prev_year:=YEAR(created_at)
            FROM (
                SELECT id, created_at
                FROM issues
                ORDER BY YEAR(created_at), created_at
            ) ordered_issues,
            (SELECT @row_number:=0, @prev_year:=NULL) vars
        ) computed_codes ON i1.id = computed_codes.id
        SET i1.issue_code = computed_codes.issue_code
    """)

    # 添加唯一索引
    op.create_index('idx_issues_issue_code', 'issues', ['issue_code'], unique=True)

    # 将字段改为 NOT NULL
    op.alter_column(
        'issues',
        'issue_code',
        nullable=False
    )


def downgrade() -> None:
    # 删除唯一索引
    op.drop_index('idx_issues_issue_code', table_name='issues')

    # 删除 issue_code 字段
    op.drop_column('issues', 'issue_code')
