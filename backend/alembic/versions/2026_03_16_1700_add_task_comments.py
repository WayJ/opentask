"""
创建评论表的数据库迁移
Revision ID: 2026_03_16_1700
Revises: 2026_03_16_1000
Create Time: 2026-03-16 17:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '2026_03_16_1700'
down_revision = '2026_03_16_1000'


def upgrade():
    """创建评论表"""
    op.create_table(
        'agent_task_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(255), nullable=False),
        sa.Column('agent_id', sa.String(255), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('comment_type', sa.String(50), nullable=False, server_default='comment'),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['agent_tasks.task_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['agent_task_comments.id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # 创建索引
    op.create_index('idx_task_id', 'agent_task_comments', ['task_id'])
    op.create_index('idx_agent_id', 'agent_task_comments', ['agent_id'])
    op.create_index('idx_user_id', 'agent_task_comments', ['user_id'])
    op.create_index('idx_task_created', 'agent_task_comments', ['task_id', 'created_at'])
    op.create_index('idx_agent_created', 'agent_task_comments', ['agent_id', 'created_at'])


def downgrade():
    """删除评论表"""
    op.drop_table('agent_task_comments')
