"""comment FTS mid: PG tsvector+GIN + SQLite FTS5 triggers on issue_comments (E62)

Revision ID: u7d8e9f0a1b5
Revises: t6c7d8e9f0a4
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u7d8e9f0a1b5"
down_revision: Union[str, None] = "t6c7d8e9f0a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pg_add_tsv() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "issue_comments" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("issue_comments")}
    if "search_tsv" not in cols:
        op.execute(
            sa.text(
                "ALTER TABLE issue_comments ADD COLUMN search_tsv tsvector "
                "GENERATED ALWAYS AS ("
                "to_tsvector('simple', left(coalesce(content,''), 16000))"
                ") STORED"
            )
        )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_issue_comments_search_tsv "
            "ON issue_comments USING GIN (search_tsv)"
        )
    )


def _sqlite_fts() -> None:
    op.execute(
        sa.text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS issue_comments_fts USING fts5(
              id UNINDEXED, issue_id UNINDEXED,
              content,
              tokenize='unicode61'
            )
            """
        )
    )
    op.execute(sa.text("DROP TRIGGER IF EXISTS issue_comments_ai"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS issue_comments_ad"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS issue_comments_au"))
    op.execute(
        sa.text(
            """
            CREATE TRIGGER issue_comments_ai AFTER INSERT ON issue_comments BEGIN
              INSERT INTO issue_comments_fts(id, issue_id, content)
              VALUES (new.id, new.issue_id, substr(coalesce(new.content,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER issue_comments_ad AFTER DELETE ON issue_comments BEGIN
              DELETE FROM issue_comments_fts WHERE id = old.id;
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER issue_comments_au AFTER UPDATE ON issue_comments BEGIN
              DELETE FROM issue_comments_fts WHERE id = old.id;
              INSERT INTO issue_comments_fts(id, issue_id, content)
              VALUES (new.id, new.issue_id, substr(coalesce(new.content,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO issue_comments_fts(id, issue_id, content)
            SELECT id, issue_id, substr(coalesce(content,''), 1, 16000)
            FROM issue_comments
            WHERE id NOT IN (SELECT id FROM issue_comments_fts)
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        _pg_add_tsv()
    elif dialect == "sqlite":
        _sqlite_fts()


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS ix_issue_comments_search_tsv"))
        op.execute(sa.text("ALTER TABLE issue_comments DROP COLUMN IF EXISTS search_tsv"))
    elif dialect == "sqlite":
        op.execute(sa.text("DROP TRIGGER IF EXISTS issue_comments_ai"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS issue_comments_ad"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS issue_comments_au"))
        op.execute(sa.text("DROP TABLE IF EXISTS issue_comments_fts"))
