"""add_document_tables

Revision ID: 8a5f2d3c9e4b
Revises: b6bfd8ff7b2c
Create Date: 2026-03-04 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a5f2d3c9e4b'
down_revision: Union[str, None] = 'b6bfd8ff7b2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 documents 表（通用模型，支持多态关联，无SQL外键）
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True, comment='文档 ID (UUID)'),
        sa.Column('entity_type', sa.String(50), nullable=False, comment='实体类型 (requirement/task/project/repo 等)'),
        sa.Column('entity_id', sa.String(36), nullable=False, comment='实体 ID'),
        sa.Column('title', sa.String(255), nullable=False, comment='文档标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='文档内容 (Markdown 格式)'),
        sa.Column('content_hash', sa.String(64), nullable=True, comment='内容哈希 (SHA-256)'),
        sa.Column('version', sa.Integer(), nullable=False, default=1, comment='当前版本号'),
        sa.Column('is_latest', sa.Boolean(), nullable=False, default=True, comment='是否为最新版本'),
        sa.Column('status', sa.String(20), nullable=False, default='DRAFT', comment='文档状态 (DRAFT/PUBLISHED/ARCHIVED)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.String(255), nullable=True, comment='创建者 ID'),
        sa.Column('updated_by', sa.String(255), nullable=True, comment='更新者 ID'),
        comment='文档表（通用模型，通过多态关联支持任何实体）'
    )

    # 创建 documents 索引
    op.create_index('idx_documents_entity', 'documents', ['entity_type', 'entity_id'])
    op.create_index('idx_documents_entity_type', 'documents', ['entity_type'])
    op.create_index('idx_documents_entity_id', 'documents', ['entity_id'])
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_documents_version', 'documents', ['version'])
    op.create_index('idx_documents_is_latest', 'documents', ['is_latest'])
    op.create_index('idx_documents_created_at', 'documents', ['created_at'])

    # 创建唯一约束 (entity_type + entity_id + version) - 确保同一实体的版本号唯一
    op.create_unique_constraint('uq_documents_entity_version', 'documents', ['entity_type', 'entity_id', 'version'])

    # 创建 document_versions 表
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(36), primary_key=True, comment='版本 ID (UUID)'),
        sa.Column('document_id', sa.String(36), nullable=False, comment='文档 ID'),
        sa.Column('version', sa.Integer(), nullable=False, comment='版本号'),
        sa.Column('content', sa.Text(), nullable=False, comment='完整内容快照'),
        sa.Column('diff', sa.Text(), nullable=True, comment='版本差异 (可选)'),
        sa.Column('change_summary', sa.Text(), nullable=True, comment='变更摘要'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('created_by', sa.String(255), nullable=True, comment='创建者 ID'),
        comment='文档版本表'
    )

    # 创建 document_versions 索引
    op.create_index('idx_document_versions_document_id', 'document_versions', ['document_id'])
    op.create_index('idx_document_versions_version', 'document_versions', ['version'])
    op.create_unique_constraint('uq_document_versions_doc_version', 'document_versions', ['document_id', 'version'])

    # 创建 document_attachments 表
    op.create_table(
        'document_attachments',
        sa.Column('id', sa.String(36), primary_key=True, comment='附件 ID (UUID)'),
        sa.Column('document_id', sa.String(36), nullable=False, comment='文档 ID'),
        sa.Column('filename', sa.String(255), nullable=False, comment='文件名'),
        sa.Column('storage_path', sa.Text(), nullable=False, comment='Supabase Storage 路径'),
        sa.Column('file_size', sa.Integer(), nullable=True, comment='文件大小 (字节)'),
        sa.Column('mime_type', sa.String(100), nullable=True, comment='MIME 类型'),
        sa.Column('width', sa.Integer(), nullable=True, comment='图片宽度 (像素)'),
        sa.Column('height', sa.Integer(), nullable=True, comment='图片高度 (像素)'),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='上传时间'),
        sa.Column('uploaded_by', sa.String(255), nullable=True, comment='上传者 ID'),
        comment='文档附件表'
    )

    # 创建 document_attachments 索引
    op.create_index('idx_document_attachments_document_id', 'document_attachments', ['document_id'])
    op.create_index('idx_document_attachments_uploaded_at', 'document_attachments', ['uploaded_at'])


def downgrade() -> None:
    # 回滚：删除表（按照依赖关系的逆序）
    op.drop_table('document_attachments')
    op.drop_table('document_versions')
    op.drop_table('documents')
