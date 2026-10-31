"""add_issue_reactions_table

Revision ID: 44ee59a7e62c
Revises: 606fee7d54c8
Create Date: 2026-03-11 14:00:43.357929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44ee59a7e62c'
down_revision: Union[str, None] = '606fee7d54c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 issue_reactions 表
    op.create_table(
        'issue_reactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('issue_id', sa.String(36), nullable=False),
        sa.Column('emoji', sa.String(10), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Issue 反应表'
    )

    # 创建索引
    op.create_index('idx_issue_reactions_issue', 'issue_reactions', ['issue_id'])
    op.create_index('idx_issue_reactions_emoji', 'issue_reactions', ['emoji'])
    op.create_index('idx_issue_reactions_user', 'issue_reactions', ['user_id'])
    op.create_index('idx_issue_reactions_issue_emoji', 'issue_reactions', ['issue_id', 'emoji'])

    # 创建唯一约束（一个用户对同一个 Issue 只能有一个相同表情的反应）
    op.create_unique_constraint('uq_issue_reaction', 'issue_reactions', ['issue_id', 'emoji', 'user_id'])


def downgrade() -> None:
    # 删除表
    op.drop_table('issue_reactions')
