"""简化文档模型为附件模型

Revision ID: simplify_document_to_attachment
Revises: 2026_03_04_1000
Create Date: 2026-03-05 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'simplify_document_to_attachment'
down_revision = '9c7e4f1a5d6c'
branch_labels = None
depends_on = None


def upgrade():
    """简化文档模型为附件模型"""

    # 1. 删除 document_attachments 表（不再需要）
    op.drop_table('document_attachments')

    # 2. 删除 document_versions 表（不再需要版本管理）
    op.drop_table('document_versions')

    # 3. 删除 documents 表的旧字段
    op.drop_constraint('uq_documents_entity_version', 'documents', type_='unique')
    op.drop_index('idx_documents_version', 'documents')
    op.drop_index('idx_documents_is_latest', 'documents')

    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_column('content')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('version')
        batch_op.drop_column('is_latest')

    # 4. 添加新的文件相关字段
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('file_path', sa.String(500), nullable=True, comment='文件存储路径'))
        batch_op.add_column(sa.Column('file_name', sa.String(255), nullable=True, comment='原始文件名'))
        batch_op.add_column(sa.Column('file_type', sa.String(100), nullable=True, comment='MIME 类型'))
        batch_op.add_column(sa.Column('file_size', sa.Integer, nullable=True, comment='文件大小（字节）'))

    # 5. 为旧数据设置 file_path（如果有 content，说明是旧文档，可以标记为已迁移）
    # 这里可以选择性地处理旧数据，或者清空表
    # op.execute("UPDATE documents SET file_path = 'MIGRATED' WHERE content IS NOT NULL")


def downgrade():
    """回滚到复杂的多层模型"""

    # 1. 删除新增的文件字段
    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_column('file_size')
        batch_op.drop_column('file_type')
        batch_op.drop_column('file_name')
        batch_op.drop_column('file_path')

    # 2. 恢复旧字段
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('content', sa.Text(), nullable=False))
        batch_op.add_column(sa.Column('content_hash', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='1'))

    # 3. 恢复索引和约束
    op.create_index('idx_documents_version', 'documents', ['version'])
    op.create_index('idx_documents_is_latest', 'documents', ['is_latest'])
    op.create_unique_constraint('uq_documents_entity_version', 'documents', ['entity_type', 'entity_id', 'version'])

    # 4. 恢复 document_versions 表
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('diff', sa.Text(), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
    )
    op.create_index('idx_document_versions_document_id', 'document_versions', ['document_id'])
    op.create_index('idx_document_versions_version', 'document_versions', ['version'])
    op.create_unique_constraint('uq_document_versions_doc_version', 'document_versions', ['document_id', 'version'])

    # 5. 恢复 document_attachments 表
    op.create_table(
        'document_attachments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('uploaded_by', sa.String(255), nullable=True),
    )
    op.create_index('idx_document_attachments_document_id', 'document_attachments', ['document_id'])
    op.create_index('idx_document_attachments_uploaded_at', 'document_attachments', ['uploaded_at'])
