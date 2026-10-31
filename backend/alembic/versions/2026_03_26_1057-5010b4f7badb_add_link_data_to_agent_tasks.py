"""add_link_data_to_agent_tasks

Revision ID: 2025_03_26_add_link_data
Revises: 2026_03_25_2110
Create Date: 2025-03-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '202603261057'
down_revision = '202603252110'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 link_data 字段
    op.add_column(
        'agent_tasks',
        sa.Column(
            'link_data',
            sa.JSON(),
            nullable=True,
            comment='关联数据列表，格式: ["issue:uuid", "requirement:uuid"]'
        )
    )


def downgrade():
    op.drop_column('agent_tasks', 'link_data')
