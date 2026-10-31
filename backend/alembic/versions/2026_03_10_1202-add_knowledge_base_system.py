"""add knowledge base system

Revision ID: 2026_03_10_1202
Revises: remove_document_title
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_03_10_1202'
down_revision = 'remove_document_title'
branch_labels = None
depends_on = None


def upgrade():
    # 创建知识库表
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(255), nullable=True),
        sa.Column('repository_url', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='active', comment='状态：active-活跃, archived-已归档'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        comment='知识库表（独立的知识管理实体）'
    )

    # 创建项目-知识库关联表
    op.create_table(
        'project_knowledge_bases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('knowledge_base_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id', 'knowledge_base_id', name='uq_project_kb'),
        comment='项目-知识库关联表（多对多）'
    )

    # 创建知识分类表
    op.create_table(
        'knowledge_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['parent_id'], ['knowledge_categories.id'], ondelete='CASCADE'),
        comment='知识分类表（树形结构）'
    )

    # 创建标签表
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('color', sa.String(20), nullable=False, default='#3b82f6'),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        comment='标签表'
    )

    # 创建知识表
    op.create_table(
        'knowledge',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('knowledge_base_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft', comment='状态：draft-草稿, published-已发布, archived-已归档'),
        sa.Column('visibility', sa.String(20), nullable=False, default='internal', comment='可见性：public-公开, internal-内部, private-私密'),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('view_count', sa.Integer(), nullable=False, default=0),
        sa.Column('like_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['knowledge_categories.id'], ondelete='SET NULL'),
        comment='知识文档表'
    )

    # ============================================================================
    # ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
    # # 创建知识-标签关联表
    # op.create_table(
    #     'knowledge_tags',
    #     sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
    #     sa.Column('knowledge_id', sa.String(36), nullable=False),
    #     sa.Column('tag_id', sa.Integer(), nullable=False),
    #     sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    #     sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge.id'], ondelete='CASCADE'),
    #     sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
    #     sa.UniqueConstraint('knowledge_id', 'tag_id'),
    #     comment='知识-标签关联表'
    # )
    # ============================================================================

    # 创建索引
    # 知识库表索引
    op.create_index('idx_knowledge_bases_status', 'knowledge_bases', ['status'])
    op.create_index('idx_knowledge_bases_created_at', 'knowledge_bases', ['created_at'])
    op.create_index('idx_knowledge_bases_name', 'knowledge_bases', ['name'])

    # 项目-知识库关联表索引
    op.create_index('idx_project_kb_project', 'project_knowledge_bases', ['project_id'])
    op.create_index('idx_project_kb_kb', 'project_knowledge_bases', ['knowledge_base_id'])

    # 知识分类表索引
    op.create_index('idx_categories_parent', 'knowledge_categories', ['parent_id'])
    op.create_index('idx_categories_sort', 'knowledge_categories', ['sort_order'])

    # 标签表索引
    op.create_index('idx_tags_usage', 'tags', ['usage_count'])

    # 知识表索引
    op.create_index('idx_knowledge_kb', 'knowledge', ['knowledge_base_id'])
    op.create_index('idx_knowledge_category', 'knowledge', ['category_id'])
    op.create_index('idx_knowledge_status', 'knowledge', ['status'])
    op.create_index('idx_knowledge_visibility', 'knowledge', ['visibility'])
    op.create_index('idx_knowledge_slug', 'knowledge', ['slug'])
    op.create_index('idx_knowledge_created_at', 'knowledge', ['created_at'])
    op.create_index('idx_knowledge_is_deleted', 'knowledge', ['is_deleted'])
    op.create_index('idx_knowledge_kb_status', 'knowledge', ['knowledge_base_id', 'status', 'is_deleted'])

    # ============================================================================
    # ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
    # # 知识-标签关联表索引
    # op.create_index('idx_knowledge_tags_knowledge', 'knowledge_tags', ['knowledge_id'])
    # op.create_index('idx_knowledge_tags_tag', 'knowledge_tags', ['tag_id'])
    # ============================================================================


def downgrade():
    # 删除表
    # ============================================================================
    # ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
    # op.drop_table('knowledge_tags')
    # ============================================================================
    op.drop_table('knowledge')
    op.drop_table('tags')
    op.drop_table('knowledge_categories')
    op.drop_table('project_knowledge_bases')
    op.drop_table('knowledge_bases')
