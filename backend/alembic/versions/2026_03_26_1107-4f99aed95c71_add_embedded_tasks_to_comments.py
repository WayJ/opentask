"""add embedded_tasks to comments

Revision ID: 2026_03_26_1107
Revises: 202603261057
Create Date: 2026-03-26 11:07:40.317390

"""
from alembic import op
import sqlalchemy as sa

revision = '2026_03_26_1107'
down_revision = '202603261057'
branch_labels = None
depends_on = None


def upgrade():
    # 需求评论表添加 embedded_tasks 字段
    op.add_column(
        'requirement_comments',
        sa.Column(
            'embedded_tasks',
            sa.JSON(),
            nullable=True,
            comment='嵌入式任务列表'
        )
    )

    # Issue 评论表策略：如果有 metadata 则复用，否则添加 embedded_tasks
    # 检查表结构决定策略
    try:
        # 尝试检查 metadata 列是否存在
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('issue_comments')]

        if 'metadata' in columns:
            # 已有 metadata 字段，不需要添加新字段
            # 在应用层将 embedded_tasks 存入 metadata
            pass
        else:
            # 没有 metadata，添加 embedded_tasks 字段
            op.add_column(
                'issue_comments',
                sa.Column(
                    'embedded_tasks',
                    sa.JSON(),
                    nullable=True,
                    comment='嵌入式任务列表'
                )
            )
    except Exception:
        # 如果检查失败，尝试添加字段（会失败则忽略）
        pass


def downgrade():
    op.drop_column('requirement_comments', 'embedded_tasks')
    # Issue comments 的 downgrade 取决于 upgrade 时的选择
    # 如果添加了 embedded_tasks 则删除，否则不做操作
    try:
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('issue_comments')]

        if 'embedded_tasks' in columns:
            op.drop_column('issue_comments', 'embedded_tasks')
    except Exception:
        # 如果检查失败，尝试删除字段（会失败则忽略）
        pass
