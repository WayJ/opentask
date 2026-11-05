"""E99: drop issues.legacy_issue_code + rebuild FTS without legacy

Revision ID: g0a1b2c3d4e5
Revises: f9a0b1c2d3e4

Forward-only. Does not rewrite E12 (b8c9d0e1f2a4) or E60 (s5b6c7d8e9f3).
Fresh DBs still ADD the column in E12 then drop it here.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g0a1b2c3d4e5"
down_revision: Union[str, None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PG_TSV_EXPR = (
    "to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(issue_code,'') || ' ' || "
    "left(coalesce(description,''), 16000))"
)


def upgrade_on_connection(bind) -> None:
    """Idempotent drop + FTS rebuild (used by alembic upgrade and directed tests)."""
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    if "issues" not in set(inspector.get_table_names()):
        return
    cols = {c["name"] for c in inspector.get_columns("issues")}

    if dialect == "postgresql":
        _pg_drop_and_rebuild(bind, cols)
    elif dialect == "sqlite":
        _sqlite_drop_and_rebuild(bind, cols)


def _pg_drop_and_rebuild(bind, cols: set[str]) -> None:
    # search_tsv may reference legacy_issue_code — drop before column
    if "search_tsv" in cols:
        bind.execute(sa.text("DROP INDEX IF EXISTS ix_issues_search_tsv"))
        bind.execute(sa.text("ALTER TABLE issues DROP COLUMN IF EXISTS search_tsv"))
        cols.discard("search_tsv")

    bind.execute(sa.text("DROP INDEX IF EXISTS ix_issues_legacy_issue_code"))
    if "legacy_issue_code" in cols:
        bind.execute(sa.text("ALTER TABLE issues DROP COLUMN IF EXISTS legacy_issue_code"))

    # Recreate tsv without legacy (idempotent if already present without legacy)
    inspector = sa.inspect(bind)
    cols2 = {c["name"] for c in inspector.get_columns("issues")}
    if "search_tsv" not in cols2:
        bind.execute(
            sa.text(
                f"ALTER TABLE issues ADD COLUMN search_tsv tsvector "
                f"GENERATED ALWAYS AS ({_PG_TSV_EXPR}) STORED"
            )
        )
    bind.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_issues_search_tsv ON issues USING GIN (search_tsv)")
    )


def _sqlite_drop_and_rebuild(bind, cols: set[str]) -> None:
    # Always rebuild FTS without legacy column so triggers cannot reference it
    bind.execute(sa.text("DROP TRIGGER IF EXISTS issues_ai"))
    bind.execute(sa.text("DROP TRIGGER IF EXISTS issues_ad"))
    bind.execute(sa.text("DROP TRIGGER IF EXISTS issues_au"))
    bind.execute(sa.text("DROP TABLE IF EXISTS issues_fts"))

    # Drop index then column when present
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_issues_legacy_issue_code"))
    if "legacy_issue_code" in cols:
        bind.execute(sa.text("ALTER TABLE issues DROP COLUMN legacy_issue_code"))

    bind.execute(
        sa.text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING fts5(
              id UNINDEXED, workspace_id UNINDEXED,
              title, issue_code, description,
              tokenize='unicode61'
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER issues_ai AFTER INSERT ON issues BEGIN
              INSERT INTO issues_fts(id, workspace_id, title, issue_code, description)
              VALUES (new.id, new.workspace_id, new.title, new.issue_code,
                      substr(coalesce(new.description,''), 1, 16000));
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER issues_ad AFTER DELETE ON issues BEGIN
              DELETE FROM issues_fts WHERE id = old.id;
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER issues_au AFTER UPDATE ON issues BEGIN
              DELETE FROM issues_fts WHERE id = old.id;
              INSERT INTO issues_fts(id, workspace_id, title, issue_code, description)
              VALUES (new.id, new.workspace_id, new.title, new.issue_code,
                      substr(coalesce(new.description,''), 1, 16000));
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO issues_fts(id, workspace_id, title, issue_code, description)
            SELECT id, workspace_id, title, issue_code,
                   substr(coalesce(description,''), 1, 16000)
            FROM issues
            WHERE id NOT IN (SELECT id FROM issues_fts)
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    upgrade_on_connection(bind)


def downgrade() -> None:
    # No recreate of legacy dual-read semantics; optional null column for chain symmetry
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "issues" not in set(inspector.get_table_names()):
        return
    cols = {c["name"] for c in inspector.get_columns("issues")}
    if "legacy_issue_code" not in cols:
        if bind.dialect.name == "postgresql":
            op.add_column(
                "issues",
                sa.Column("legacy_issue_code", sa.String(50), nullable=True),
            )
            op.create_index("ix_issues_legacy_issue_code", "issues", ["legacy_issue_code"])
        else:
            bind.execute(sa.text("ALTER TABLE issues ADD COLUMN legacy_issue_code VARCHAR(50)"))
