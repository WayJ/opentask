"""add project_id to requirements

Revision ID: add_project_id
Revises: 105845b0ee19
Create Date: 2026-02-25 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_project_id'
down_revision: Union[str, None] = '105845b0ee19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 检查并添加 project_id 字段
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('requirements')]

    if 'project_id' not in columns:
        op.add_column('requirements', sa.Column('project_id', sa.String(36), nullable=True))

    # 检查并创建索引
    indexes = inspector.get_indexes('requirements')
    if not any(idx['name'] == 'idx_requirements_project_id' for idx in indexes):
        op.create_index('idx_requirements_project_id', 'requirements', ['project_id'])

    # 添加外键约束
    try:
        conn = op.get_bind()
        conn.execute(sa.text(
            "ALTER TABLE requirements "
            "ADD CONSTRAINT fk_requirements_project_id_projects "
            "FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE"
        ))
    except Exception:
        pass  # 外键可能已存在


def downgrade() -> None:
    # 删除外键
    try:
        op.drop_constraint('fk_requirements_project_id_projects', 'requirements', type_='foreignkey')
    except Exception:
        pass

    # 删除索引
    try:
        op.drop_index('idx_requirements_project_id', table_name='requirements')
    except Exception:
        pass

    # 删除字段
    op.drop_column('requirements', 'project_id')
