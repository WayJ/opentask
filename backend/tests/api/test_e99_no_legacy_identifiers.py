"""E99: KEY-N only — no legacy dual-read, no year codec, schema drop."""
from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from opentask.api.jira.keys import KEY_N_BASE, issue_code_to_key, key_to_issue_code
from opentask.models.issue.model import Issue


def _auth(token: str, workspace_id: str | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h


async def _register(client: AsyncClient, prefix: str) -> dict:
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


@pytest.mark.asyncio
async def test_e99_key_n_by_code_200(test_client: AsyncClient):
    user = await _register(test_client, "e99ok")
    created = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "E99 KEY-N", "type": "bug"},
    )
    assert created.status_code == 200, created.text
    code = created.json()["data"]["issue_code"]
    assert "-" in code and not code.upper().startswith("ISSUE20")
    resp = await test_client.get(
        f"/api/issues/{code}",
        params={"by_code": "true"},
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["issue_code"] == code


@pytest.mark.asyncio
async def test_e99_year_by_code_404(test_client: AsyncClient):
    user = await _register(test_client, "e99yr")
    resp = await test_client.get(
        "/api/issues/ISSUE2026-1",
        params={"by_code": "true"},
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 404


def test_e99_orm_has_no_legacy_attr():
    assert not hasattr(Issue, "legacy_issue_code") or "legacy_issue_code" not in {
        c.key for c in Issue.__table__.columns
    }
    assert "legacy_issue_code" not in {c.key for c in Issue.__table__.columns}


def test_e99_jira_key_n_roundtrip_and_year_rejected():
    key = issue_code_to_key("OT-1")
    assert key_to_issue_code(key) == "OT-1"
    with pytest.raises(ValueError):
        issue_code_to_key("ISSUE2026-3")
    with pytest.raises(ValueError):
        key_to_issue_code("OPENTASK-2026000000003")
    with pytest.raises(ValueError):
        key_to_issue_code(f"OPENTASK-{KEY_N_BASE - 1}")


def _load_drop_mod():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "2026_11_05_5900-g0a1b2c3d4e5_e99_drop_legacy_issue_code.py"
    )
    spec = importlib.util.spec_from_file_location("e99_drop", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_e99_drop_migration_removes_column(test_engine: AsyncEngine):
    """Apply drop upgrade against a table that still has the legacy column."""
    import sqlalchemy as sa

    mod = _load_drop_mod()
    assert mod.revision == "g0a1b2c3d4e5"
    assert mod.down_revision == "f9a0b1c2d3e4"

    def _ensure_and_drop(sync_conn):
        dialect = sync_conn.dialect.name
        cols = {c["name"] for c in sa.inspect(sync_conn).get_columns("issues")}
        if "legacy_issue_code" not in cols:
            if dialect == "sqlite":
                sync_conn.execute(sa.text("ALTER TABLE issues ADD COLUMN legacy_issue_code VARCHAR(50)"))
            else:
                sync_conn.execute(
                    sa.text("ALTER TABLE issues ADD COLUMN IF NOT EXISTS legacy_issue_code VARCHAR(50)")
                )
                sync_conn.execute(
                    sa.text(
                        "CREATE INDEX IF NOT EXISTS ix_issues_legacy_issue_code "
                        "ON issues (legacy_issue_code)"
                    )
                )
        mod.upgrade_on_connection(sync_conn)
        cols2 = {c["name"] for c in sa.inspect(sync_conn).get_columns("issues")}
        assert "legacy_issue_code" not in cols2

    async with test_engine.begin() as conn:
        await conn.run_sync(_ensure_and_drop)
