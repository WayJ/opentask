"""E60: SearchBackend dialect resolution + SQLite FTS5 unit tests."""
from __future__ import annotations

from unittest import mock

from sqlalchemy import create_engine, text


def test_resolve_backend_unknown_dialect_uses_ilike():
    from opentask.services.search.backend import (
        ILikeSearchBackend,
        resolve_search_backend,
    )

    session = mock.MagicMock()
    session.bind.dialect.name = "mysql"
    backend = resolve_search_backend(session)
    assert isinstance(backend, ILikeSearchBackend)


def test_resolve_backend_postgresql():
    from opentask.services.search.backend import (
        PostgresFTSBackend,
        resolve_search_backend,
    )

    session = mock.MagicMock()
    session.bind.dialect.name = "postgresql"
    backend = resolve_search_backend(session)
    assert isinstance(backend, PostgresFTSBackend)


def test_resolve_backend_sqlite():
    from opentask.services.search.backend import (
        SQLiteFTSBackend,
        resolve_search_backend,
    )

    session = mock.MagicMock()
    session.bind.dialect.name = "sqlite"
    backend = resolve_search_backend(session)
    assert isinstance(backend, SQLiteFTSBackend)


def test_sqlite_fts5_trigger_sync_and_match():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE issues (
              id TEXT PRIMARY KEY,
              workspace_id TEXT NOT NULL,
              title TEXT NOT NULL,
              issue_code TEXT NOT NULL,
              legacy_issue_code TEXT,
              description TEXT,
              status TEXT,
              priority TEXT,
              updated_at TEXT
            );
            """
        ))
        conn.execute(text(
            """
            CREATE VIRTUAL TABLE issues_fts USING fts5(
              id UNINDEXED, workspace_id UNINDEXED,
              title, issue_code, legacy_issue_code, description,
              tokenize='unicode61'
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TRIGGER issues_ai AFTER INSERT ON issues BEGIN
              INSERT INTO issues_fts(id, workspace_id, title, issue_code, legacy_issue_code, description)
              VALUES (new.id, new.workspace_id, new.title, new.issue_code,
                      coalesce(new.legacy_issue_code,''), substr(coalesce(new.description,''),1,16000));
            END;
            """
        ))
        conn.execute(text(
            """
            CREATE TRIGGER issues_ad AFTER DELETE ON issues BEGIN
              DELETE FROM issues_fts WHERE id = old.id;
            END;
            """
        ))
        conn.execute(text(
            """
            CREATE TRIGGER issues_au AFTER UPDATE ON issues BEGIN
              DELETE FROM issues_fts WHERE id = old.id;
              INSERT INTO issues_fts(id, workspace_id, title, issue_code, legacy_issue_code, description)
              VALUES (new.id, new.workspace_id, new.title, new.issue_code,
                      coalesce(new.legacy_issue_code,''), substr(coalesce(new.description,''),1,16000));
            END;
            """
        ))
        conn.execute(
            text(
                "INSERT INTO issues(id, workspace_id, title, issue_code, description, status, priority, updated_at) "
                "VALUES ('i1','ws1','T','OT-1','needle in body','open','medium','2026-01-01')"
            )
        )
        rows = conn.execute(
            text("SELECT id FROM issues_fts WHERE issues_fts MATCH 'needle' AND workspace_id='ws1'")
        ).fetchall()
        assert rows and rows[0][0] == "i1"
        conn.execute(text("DELETE FROM issues WHERE id='i1'"))
        rows2 = conn.execute(
            text("SELECT id FROM issues_fts WHERE issues_fts MATCH 'needle'")
        ).fetchall()
        assert rows2 == []
