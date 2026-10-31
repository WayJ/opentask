"""add_requirement_code_field

Revision ID: 514b5d1f86fa
Revises: a3d0c3792864
Create Date: 2026-02-25 03:41:53.822167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '514b5d1f86fa'
down_revision: Union[str, None] = 'a3d0c3792864'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 code 字段
    op.add_column('requirements', sa.Column('code', sa.String(50), nullable=True))

    # 创建需求编码序列表 (MySQL 不支持 CheckConstraint 的 name 参数)
    op.create_table(
        'requirement_code_sequence',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('year', sa.Integer, nullable=False, unique=True),
        sa.Column('sequence', sa.Integer, nullable=False, server_default='0')
    )

    # 为当前年份创建序列记录
    current_year = datetime.now().year
    op.execute(
        sa.insert(table('requirement_code_sequence',
                      column('year'),
                      column('sequence')))
        .values(year=current_year, sequence=0)
    )

    # 为现有需求生成编码
    connection = op.get_bind()
    existing_requirements = connection.execute(
        sa.text("SELECT id FROM requirements ORDER BY created_at")
    ).fetchall()

    for idx, (req_id,) in enumerate(existing_requirements, start=1):
        code = f"需求{current_year}-{idx}"
        connection.execute(
            sa.text("UPDATE requirements SET code = :code WHERE id = :id"),
            {"code": code, "id": req_id}
        )

    # 更新序列值
    connection.execute(
        sa.text("UPDATE requirement_code_sequence SET sequence = :seq WHERE year = :year"),
        {"seq": len(existing_requirements), "year": current_year}
    )

    # 使 code 字段非空
    op.alter_column('requirements', 'code', nullable=False)

    # 创建索引
    op.create_index('idx_requirements_code', 'requirements', ['code'])
    op.create_index('idx_requirements_code_sequence_year', 'requirement_code_sequence', ['year'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_requirements_code_sequence_year', table_name='requirement_code_sequence')
    op.drop_index('idx_requirements_code', table_name='requirements')

    # 删除 code 字段
    op.drop_column('requirements', 'code')

    # 删除序列表
    op.drop_table('requirement_code_sequence')
