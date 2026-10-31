"""initial migration

OpenTask 项目初始迁移，包含所有核心数据表：
- 用户表 (user)
- 数据库连接表 (connections)
- 对话表 (conversations)
- 消息表 (messages)
- 结果表 (results)
- 媒体表 (media)
- 项目管理表 (projects)
- 仓库配置表 (repo_configs)
- 需求表 (requirements)
- 事件表 (events)
- 需求-仓库关联表 (requirement_repos)
- 评论表 (comments)
- 队列任务表 (queue_jobs)

Revision ID: 202602231200
Revises:
Create Date: 2026-02-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '202602231200'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # 用户表 (user)
    # ==========================================================================
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('openai_api_key', sa.String(255), nullable=True),
        sa.Column('preferred_openai_model', sa.String(100), nullable=True),
        sa.Column('langsmith_api_key', sa.String(255), nullable=True),
        sa.Column('sentry_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('analytics_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('hide_sql_preference', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('openai_base_url', sa.String(255), nullable=True),
    )

    # ==========================================================================
    # 数据库连接表 (connections)
    # ==========================================================================
    op.create_table(
        'connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dsn', sa.String(500), nullable=False, unique=True),
        sa.Column('database', sa.String(100), nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('dialect', sa.String(50), nullable=True),
        sa.Column('is_sample', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('options', sa.JSON(), nullable=True),
    )

    # ==========================================================================
    # 对话表 (conversations)
    # ==========================================================================
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('conversation_type', sa.String(50), nullable=False, server_default='sql_chat'),
        sa.Column('workspace_id', sa.Text(), nullable=True),
        sa.Column('ai_settings', sa.Text(), nullable=True),
    )
    op.create_index('idx_conversations_connection_id', 'conversations', ['connection_id'])

    # ==========================================================================
    # 消息表 (messages)
    # ==========================================================================
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
    )
    op.create_index('idx_messages_conversation_id', 'messages', ['conversation_id'])

    # ==========================================================================
    # 结果表 (results)
    # ==========================================================================
    op.create_table(
        'results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('linked_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index('idx_results_message_id', 'results', ['message_id'])

    # ==========================================================================
    # 媒体表 (media)
    # ==========================================================================
    op.create_table(
        'media',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('blob', sa.LargeBinary(), nullable=False),
    )

    # ==========================================================================
    # 项目表 (projects)
    # ==========================================================================
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_projects_is_active', 'projects', ['is_active'])

    # ==========================================================================
    # 仓库配置表 (repo_configs)
    # ==========================================================================
    op.create_table(
        'repo_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('main_branch', sa.String(100), nullable=False, server_default='main'),
        sa.Column('local_path', sa.String(500), nullable=False),
        sa.Column('credentials', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_repo_configs_project_name', 'repo_configs', ['project_id', 'name'], unique=True)

    # ==========================================================================
    # 需求表 (requirements)
    # ==========================================================================
    op.create_table(
        'requirements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('priority', sa.String(50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('assignee_id', sa.String(255), nullable=True),
    )
    op.create_index('idx_requirements_status', 'requirements', ['status'])
    op.create_index('idx_requirements_priority', 'requirements', ['priority'])
    op.create_index('idx_requirements_created_at', 'requirements', ['created_at'])
    op.create_index('idx_requirements_assignee_id', 'requirements', ['assignee_id'])

    # ==========================================================================
    # 事件表 (events) - 事件溯源
    # ==========================================================================
    op.create_table(
        'events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(36), sa.ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('actor', sa.String(255), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('snapshot', sa.JSON(), nullable=True),
    )
    op.create_index('idx_events_requirement_id', 'events', ['requirement_id'])
    op.create_index('idx_events_timestamp', 'events', ['timestamp'])
    op.create_index('idx_events_type', 'events', ['type'])

    # ==========================================================================
    # 需求-仓库关联表 (requirement_repos)
    # ==========================================================================
    op.create_table(
        'requirement_repos',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(36), sa.ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('repo_id', sa.Integer(), sa.ForeignKey('repo_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch', sa.String(255), nullable=True),
        sa.Column('pr_url', sa.String(500), nullable=True),
        sa.Column('merge_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_requirement_repos_requirement_repo', 'requirement_repos', ['requirement_id', 'repo_id'], unique=True)
    op.create_index('idx_requirement_repos_repo_id', 'requirement_repos', ['repo_id'])

    # ==========================================================================
    # 评论表 (comments)
    # ==========================================================================
    op.create_table(
        'comments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(36), sa.ForeignKey('requirements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_comments_requirement_id', 'comments', ['requirement_id'])
    op.create_index('idx_comments_created_at', 'comments', ['created_at'])

    # ==========================================================================
    # 队列任务表 (queue_jobs)
    # ==========================================================================
    op.create_table(
        'queue_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requirement_id', sa.String(255), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_queue_jobs_requirement_id', 'queue_jobs', ['requirement_id'])
    op.create_index('idx_queue_jobs_status', 'queue_jobs', ['status'])
    op.create_index('idx_queue_jobs_type', 'queue_jobs', ['type'])


def downgrade() -> None:
    # 按照依赖关系逆序删除表
    op.drop_table('queue_jobs')
    op.drop_table('comments')
    op.drop_table('requirement_repos')
    op.drop_table('events')
    op.drop_table('requirements')
    op.drop_table('repo_configs')
    op.drop_table('projects')
    op.drop_table('media')
    op.drop_table('results')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('connections')
    op.drop_table('user')
