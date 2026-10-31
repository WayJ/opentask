"""移除文档的 title 字段，只使用 file_name

Revision ID: remove_document_title
Revises: simplify_document_to_attachment
Create Date: 2026-03-05 13:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_document_title'
down_revision = 'simplify_document_to_attachment'
branch_labels = None
depends_on = None


def upgrade():
    """移除 title 字段，文档只使用文件名"""
    # 删除 title 列
    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_column('title')


def downgrade():
    """恢复 title 字段"""
    # 添加回 title 列
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(255), nullable=False))
