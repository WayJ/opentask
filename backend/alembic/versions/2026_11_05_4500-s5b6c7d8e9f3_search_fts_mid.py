"""search FTS mid: PG tsvector+GIN + SQLite FTS5 triggers (E60)

Revision ID: s5b6c7d8e9f3
Revises: r4a5b6c7d8e2
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s5b6c7d8e9f3"
down_revision: Union[str, None] = "r4a5b6c7d8e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pg_add_tsv(table: str, expr: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns(table)}
    if "search_tsv" not in cols:
        op.execute(
            sa.text(
                f"ALTER TABLE {table} ADD COLUMN search_tsv tsvector "
                f"GENERATED ALWAYS AS ({expr}) STORED"
            )
        )
    op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} USING GIN (search_tsv)"))


def _sqlite_fts() -> None:
    # issues
    op.execute(
        sa.text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING fts5(
              id UNINDEXED, workspace_id UNINDEXED,
              title, issue_code, legacy_issue_code, description,
              tokenize='unicode61'
            )
            """
        )
    )
    op.execute(sa.text("DROP TRIGGER IF EXISTS issues_ai"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS issues_ad"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS issues_au"))
    op.execute(
        sa.text(
            """
            CREATE TRIGGER issues_ai AFTER INSERT ON issues BEGIN
              INSERT INTO issues_fts(id, workspace_id, title, issue_code, legacy_issue_code, description)
              VALUES (new.id, new.workspace_id, new.title, new.issue_code,
                      coalesce(new.legacy_issue_code,''),
                      substr(coalesce(new.description,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER issues_ad AFTER DELETE ON issues BEGIN
              DELETE FROM issues_fts WHERE id = old.id;
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER issues_au AFTER UPDATE ON issues BEGIN
              DELETE FROM issues_fts WHERE id = old.id;
              INSERT INTO issues_fts(id, workspace_id, title, issue_code, legacy_issue_code, description)
              VALUES (new.id, new.workspace_id, new.title, new.issue_code,
                      coalesce(new.legacy_issue_code,''),
                      substr(coalesce(new.description,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO issues_fts(id, workspace_id, title, issue_code, legacy_issue_code, description)
            SELECT id, workspace_id, title, issue_code,
                   coalesce(legacy_issue_code,''),
                   substr(coalesce(description,''), 1, 16000)
            FROM issues
            WHERE id NOT IN (SELECT id FROM issues_fts)
            """
        )
    )

    # projects
    op.execute(
        sa.text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
              id UNINDEXED, workspace_id UNINDEXED,
              name, description,
              tokenize='unicode61'
            )
            """
        )
    )
    op.execute(sa.text("DROP TRIGGER IF EXISTS projects_ai"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS projects_ad"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS projects_au"))
    op.execute(
        sa.text(
            """
            CREATE TRIGGER projects_ai AFTER INSERT ON projects BEGIN
              INSERT INTO projects_fts(id, workspace_id, name, description)
              VALUES (new.id, new.workspace_id, new.name,
                      substr(coalesce(new.description,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER projects_ad AFTER DELETE ON projects BEGIN
              DELETE FROM projects_fts WHERE id = old.id;
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER projects_au AFTER UPDATE ON projects BEGIN
              DELETE FROM projects_fts WHERE id = old.id;
              INSERT INTO projects_fts(id, workspace_id, name, description)
              VALUES (new.id, new.workspace_id, new.name,
                      substr(coalesce(new.description,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO projects_fts(id, workspace_id, name, description)
            SELECT id, workspace_id, name, substr(coalesce(description,''), 1, 16000)
            FROM projects
            WHERE id NOT IN (SELECT id FROM projects_fts)
            """
        )
    )

    # entity_documents
    op.execute(
        sa.text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS entity_documents_fts USING fts5(
              id UNINDEXED, workspace_id UNINDEXED,
              title, body_md,
              tokenize='unicode61'
            )
            """
        )
    )
    op.execute(sa.text("DROP TRIGGER IF EXISTS entity_documents_ai"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS entity_documents_ad"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS entity_documents_au"))
    op.execute(
        sa.text(
            """
            CREATE TRIGGER entity_documents_ai AFTER INSERT ON entity_documents BEGIN
              INSERT INTO entity_documents_fts(id, workspace_id, title, body_md)
              VALUES (new.id, new.workspace_id, new.title,
                      substr(coalesce(new.body_md,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER entity_documents_ad AFTER DELETE ON entity_documents BEGIN
              DELETE FROM entity_documents_fts WHERE id = old.id;
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER entity_documents_au AFTER UPDATE ON entity_documents BEGIN
              DELETE FROM entity_documents_fts WHERE id = old.id;
              INSERT INTO entity_documents_fts(id, workspace_id, title, body_md)
              VALUES (new.id, new.workspace_id, new.title,
                      substr(coalesce(new.body_md,''), 1, 16000));
            END
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO entity_documents_fts(id, workspace_id, title, body_md)
            SELECT id, workspace_id, title, substr(coalesce(body_md,''), 1, 16000)
            FROM entity_documents
            WHERE id NOT IN (SELECT id FROM entity_documents_fts)
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        _pg_add_tsv(
            "issues",
            "to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(issue_code,'') || ' ' || "
            "coalesce(legacy_issue_code,'') || ' ' || left(coalesce(description,''), 16000))",
            "ix_issues_search_tsv",
        )
        _pg_add_tsv(
            "projects",
            "to_tsvector('simple', coalesce(name,'') || ' ' || left(coalesce(description,''), 16000))",
            "ix_projects_search_tsv",
        )
        _pg_add_tsv(
            "entity_documents",
            "to_tsvector('simple', coalesce(title,'') || ' ' || left(coalesce(body_md,''), 16000))",
            "ix_entity_documents_search_tsv",
        )
    elif dialect == "sqlite":
        _sqlite_fts()


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        for table, index in (
            ("issues", "ix_issues_search_tsv"),
            ("projects", "ix_projects_search_tsv"),
            ("entity_documents", "ix_entity_documents_search_tsv"),
        ):
            op.execute(sa.text(f"DROP INDEX IF EXISTS {index}"))
            inspector = sa.inspect(bind)
            if table in inspector.get_table_names():
                cols = {c["name"] for c in inspector.get_columns(table)}
                if "search_tsv" in cols:
                    op.drop_column(table, "search_tsv")
    elif dialect == "sqlite":
        for trig in (
            "issues_ai", "issues_ad", "issues_au",
            "projects_ai", "projects_ad", "projects_au",
            "entity_documents_ai", "entity_documents_ad", "entity_documents_au",
        ):
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trig}"))
        for tbl in ("issues_fts", "projects_fts", "entity_documents_fts"):
            op.execute(sa.text(f"DROP TABLE IF EXISTS {tbl}"))
