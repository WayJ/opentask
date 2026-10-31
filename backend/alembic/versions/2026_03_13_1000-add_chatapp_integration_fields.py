"""
add chatapp integration fields

为 conversations 和 messages 表添加 ChatApp 所需的字段

Revision ID: 2026_03_13_1000
Revises: 2026_03_12_1000
Create Date: 2026-03-13 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2026_03_13_1000'
down_revision = 'c3d4e5f6g7h8'  # 修复：使用正确的 revision ID 而不是文件名
branch_labels = None
depends_on = None


def upgrade():
    """添加 ChatApp 所需的字段和索引"""

    # ============================================
    # 1. 为 conversations 表添加 ChatApp 字段
    # ============================================

    # 检查并添加 connection_id 字段
    op.add_column('conversations',
        sa.Column('connection_id', sa.CHAR(36), nullable=True,
                  comment='连接 ID')
    )

    # 检查并添加 conversation_type 字段
    op.add_column('conversations',
        sa.Column('conversation_type', sa.String(50), nullable=False,
                  server_default='normal_chat', comment='对话类型')
    )

    # 检查并添加 workspace_id 字段
    op.add_column('conversations',
        sa.Column('workspace_id', sa.String(36), nullable=True,
                  comment='工作区 ID')
    )

    # 检查并添加 ai_settings 字段
    op.add_column('conversations',
        sa.Column('ai_settings', sa.TEXT, nullable=True,
                  comment='AI 设置 (JSON)')
    )

    # ⭐ 检查并添加 user_id 字段（关键！用于用户数据隔离）
    op.add_column('conversations',
        sa.Column('user_id', sa.String(50), nullable=False,
                  server_default='guest', comment='用户 ID (关联 user 表)')
    )

    # ============================================
    # 2. 添加索引以提升查询性能
    # ============================================

    # user_id 索引（ChatApp 需要频繁查询）
    try:
        op.create_index('idx_conversations_user_id', 'conversations', ['user_id'])
    except Exception:
        # 索引可能已存在
        pass

    # connection_id 索引
    try:
        op.create_index('idx_conversations_connection_id', 'conversations', ['connection_id'])
    except Exception:
        pass

    # conversation_type 索引
    try:
        op.create_index('idx_conversations_type', 'conversations', ['conversation_type'])
    except Exception:
        pass

    # ============================================
    # 3. 为 messages 表添加 options 字段
    # ============================================

    # ⭐ options 字段用于存储 tool_use 和 tool_result 的额外信息
    op.add_column('messages',
        sa.Column('options', sa.JSON, nullable=True,
                  comment='消息选项（工具调用等）')
    )


def downgrade():
    """回滚迁移"""

    # 删除 messages 表的 options 字段
    try:
        op.drop_column('messages', 'options')
    except Exception:
        pass

    # 删除索引
    try:
        op.drop_index('idx_conversations_type', 'conversations')
    except Exception:
        pass

    try:
        op.drop_index('idx_conversations_connection_id', 'conversations')
    except Exception:
        pass

    try:
        op.drop_index('idx_conversations_user_id', 'conversations')
    except Exception:
        pass

    # 删除 conversations 表的字段
    try:
        op.drop_column('conversations', 'user_id')
    except Exception:
        pass

    try:
        op.drop_column('conversations', 'ai_settings')
    except Exception:
        pass

    try:
        op.drop_column('conversations', 'workspace_id')
    except Exception:
        pass

    try:
        op.drop_column('conversations', 'conversation_type')
    except Exception:
        pass

    try:
        op.drop_column('conversations', 'connection_id')
    except Exception:
        pass
