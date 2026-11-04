"""documents attachment table (E11-S4 smoke P0)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0

Issue attachments API queries ``documents``; table existed only via
SQLAlchemy create_all in pytest, never via Alembic — live DB 500.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "documents" in tables:
        return

    # Idempotent enum (may exist from prior create_all / partial runs)
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE documentstatus AS ENUM ('DRAFT', 'PUBLISHED', 'ARCHIVED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    document_status = postgresql.ENUM(
        "DRAFT",
        "PUBLISHED",
        "ARCHIVED",
        name="documentstatus",
        create_type=False,
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False, comment="实体类型"),
        sa.Column("entity_id", sa.String(36), nullable=False, comment="实体 ID"),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            document_status,
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column(
            "dept_id",
            sa.String(36),
            sa.ForeignKey("department.id"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "file_name",
            name="uq_document_entity_filename",
        ),
    )
    op.create_index("ix_documents_entity_type", "documents", ["entity_type"])
    op.create_index("ix_documents_entity_id", "documents", ["entity_id"])
    op.create_index("idx_documents_entity", "documents", ["entity_type", "entity_id"])
    op.create_index("idx_documents_status", "documents", ["status"])
    op.create_index("idx_documents_created_at", "documents", ["created_at"])
    op.create_index("ix_documents_dept_id", "documents", ["dept_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "documents" in set(inspector.get_table_names()):
        op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS documentstatus")
