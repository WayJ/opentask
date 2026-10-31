"""add issue tracking system

Revision ID: 2026_03_10_1203
Revises: 2026_03_10_1202
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_03_10_1203'
down_revision = '2026_03_10_1202'
branch_labels = None
depends_on = None


def upgrade():
    # 清理可能存在的旧表（开发环境）
    op.execute("DROP TABLE IF EXISTS issue_tags")
    op.execute("DROP TABLE IF EXISTS issue_timeline")
    op.execute("DROP TABLE IF EXISTS issue_relations")
    op.execute("DROP TABLE IF EXISTS issue_comments")
    op.execute("DROP TABLE IF EXISTS issues")

    # MySQL ENUM 类型（在列定义中直接使用）
    issue_type_enum = sa.Enum(
        'bug', 'feature', 'question', 'feedback', 'incident', 'improvement',
        name='issue_type'
    )
    issue_status_enum = sa.Enum(
        'open', 'in_progress', 'feedback', 'resolved', 'closed', 'rejected',
        name='issue_status'
    )
    issue_priority_enum = sa.Enum(
        'low', 'medium', 'high', 'critical',
        name='issue_priority'
    )
    comment_type_enum = sa.Enum(
        'comment', 'system', 'status_change', 'assignment', 'priority_change',
        name='comment_type'
    )
    relation_type_enum = sa.Enum(
        'blocks', 'is_blocked_by', 'relates_to', 'duplicates',
        'is_duplicated_by', 'depends_on', 'is_depended_by',
        name='relation_type'
    )
    timeline_action_enum = sa.Enum(
        'created', 'updated', 'commented', 'status_changed', 'assigned',
        'priority_changed', 'due_date_changed', 'relation_added',
        'relation_removed', 'attachment_added', 'attachment_removed',
        'label_added', 'label_removed', 'resolved', 'closed', 'reopened',
        name='timeline_action'
    )

    # 创建 issues 表
    op.create_table(
        'issues',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', issue_type_enum, nullable=False),
        sa.Column('status', issue_status_enum, nullable=False, server_default='open'),
        sa.Column('priority', issue_priority_enum, nullable=False, server_default='medium'),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('task_id', sa.String(36), nullable=True),
        sa.Column('requirement_id', sa.String(36), nullable=True),
        sa.Column('assignee_id', sa.String(255), nullable=True),
        sa.Column('reporter_id', sa.String(255), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('attachment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.TIMESTAMP(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('resolved_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('closed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('estimated_hours', sa.NUMERIC(5, 2), nullable=True),
        sa.Column('actual_hours', sa.NUMERIC(5, 2), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True)
        # 注意：暂时不创建外键约束，因为相关表可能不存在
        # sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        # sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        # sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='SET NULL')
    )

    # 创建索引
    op.create_index('idx_issues_type', 'issues', ['type'])
    op.create_index('idx_issues_status', 'issues', ['status'])
    op.create_index('idx_issues_priority', 'issues', ['priority'])
    op.create_index('idx_issues_project', 'issues', ['project_id'])
    op.create_index('idx_issues_assignee', 'issues', ['assignee_id'])
    op.create_index('idx_issues_reporter', 'issues', ['reporter_id'])
    op.create_index('idx_issues_created_at', 'issues', [sa.text('created_at DESC')])
    op.create_index('idx_issues_updated_at', 'issues', [sa.text('updated_at DESC')])
    op.create_index('idx_issues_due_date', 'issues', ['due_date'])

    # 复合索引
    op.create_index(
        'idx_issues_project_status',
        'issues',
        ['project_id', 'status']
    )
    op.create_index(
        'idx_issues_assignee_status',
        'issues',
        ['assignee_id', 'status']
    )

    # 全文搜索索引（MySQL FULLTEXT）
    op.execute("""
        CREATE FULLTEXT INDEX idx_issues_content_search
        ON issues(title, description)
    """)

    # 创建 issue_comments 表
    op.create_table(
        'issue_comments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('issue_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.String(36), nullable=True),
        sa.Column('comment_type', comment_type_enum, nullable=False, server_default='comment'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['issue_comments.id'], ondelete='CASCADE')
    )

    op.create_index('idx_issue_comments_issue', 'issue_comments', ['issue_id', sa.text('created_at DESC')])
    op.create_index('idx_issue_comments_parent', 'issue_comments', ['parent_id'])
    op.create_index('idx_issue_comments_user', 'issue_comments', ['user_id'])

    # 创建 issue_relations 表
    op.create_table(
        'issue_relations',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('source_id', sa.String(36), nullable=False),
        sa.Column('target_id', sa.String(36), nullable=False),
        sa.Column('relation_type', relation_type_enum, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['issues.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('source_id', 'target_id', 'relation_type', name='uq_issue_relation')
    )

    op.create_index('idx_issue_relations_source', 'issue_relations', ['source_id'])
    op.create_index('idx_issue_relations_target', 'issue_relations', ['target_id'])
    op.create_index('idx_issue_relations_type', 'issue_relations', ['relation_type'])

    # 创建 issue_timeline 表
    op.create_table(
        'issue_timeline',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('issue_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('action_type', timeline_action_enum, nullable=False),
        sa.Column('action_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE')
    )

    op.create_index('idx_issue_timeline_issue', 'issue_timeline', ['issue_id', sa.text('created_at DESC')])
    op.create_index('idx_issue_timeline_user', 'issue_timeline', ['user_id'])
    op.create_index('idx_issue_timeline_type', 'issue_timeline', ['action_type'])

    # 创建 tags 表（如果不存在）
    # 注意：如果表已存在（从知识库迁移创建的），则添加 type 字段
    op.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            color VARCHAR(20) NOT NULL DEFAULT '#3b82f6',
            usage_count INT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 如果 tags 表已存在但缺少 type 字段，则添加
    # 注意：MySQL 不支持 ALTER TABLE ... IF NOT EXISTS，使用 try-catch 处理
    try:
        op.execute("""
            ALTER TABLE tags
            ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'other'
            AFTER color
        """)
    except Exception:
        # 列可能已存在，忽略错误
        pass

    # 创建 issue_tags 关联表
    op.create_table(
        'issue_tags',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('issue_id', sa.String(36), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('issue_id', 'tag_id')
    )

    op.create_index('idx_issue_tags_issue', 'issue_tags', ['issue_id'])
    op.create_index('idx_issue_tags_tag', 'issue_tags', ['tag_id'])

    # 插入默认标签数据（使用 ON DUPLICATE KEY UPDATE 避免重复）
    op.execute("""
        INSERT IGNORE INTO tags (name, color, type) VALUES
        ('紧急', '#ef4444', 'severity'),
        ('线上问题', '#dc2626', 'severity'),
        ('功能缺陷', '#f59e0b', 'type'),
        ('前端', '#3b82f6', 'module'),
        ('后端', '#8b5cf6', 'module'),
        ('数据库', '#ec4899', 'module'),
        ('部署', '#06b6d4', 'module'),
        ('需要讨论', '#eab308', 'other'),
        ('已确认', '#22c55e', 'status'),
        ('无法复现', '#6b7280', 'status')
    """)


def downgrade():
    # 删除表（按依赖顺序）
    op.execute("DROP TABLE IF EXISTS issue_tags")
    op.execute("DROP TABLE IF EXISTS issue_timeline")
    op.execute("DROP TABLE IF EXISTS issue_relations")
    op.execute("DROP TABLE IF EXISTS issue_comments")
    op.execute("DROP TABLE IF EXISTS issues")
    op.execute("DROP TABLE IF EXISTS tags")
