"""E98: Linear-style Issue Identifiers harden — KEY-N only on create."""
from __future__ import annotations

import re
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.issue_service import IssueService
from opentask.services.workspace.issue_create_ws import (
    WORKSPACE_REQUIRED_DETAIL,
    WorkspaceRequiredError,
    resolve_workspace_for_issue_create,
)


KEY_N = re.compile(r"^[A-Z0-9]{2,6}-\d+$")
YEAR_CODE = re.compile(r"^ISSUE\d{4}-\d+$")


async def _register(client: AsyncClient, prefix: str = "e98"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


@pytest.mark.asyncio
async def test_generate_issue_code_none_raises(test_engine: AsyncEngine):
    async with test_engine.connect() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            svc = IssueService(session)
            with pytest.raises(ValueError, match="workspace"):
                await svc._generate_issue_code(None)
        finally:
            await session.close()


@pytest.mark.asyncio
async def test_api_explicit_ws_creates_key_n(test_client: AsyncClient, test_engine: AsyncEngine):
    user = await _register(test_client, "e98ex")
    ws = (
        await test_client.get(
            f"/api/workspaces/{user['workspaceId']}",
            headers=_auth(user["token"]),
        )
    ).json()["data"]
    key = ws["issueKey"]
    resp = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "E98 explicit", "type": "bug"},
    )
    assert resp.status_code == 200, resp.text
    code = resp.json()["data"]["issue_code"]
    assert KEY_N.match(code), code
    assert code.startswith(f"{key}-")
    assert not YEAR_CODE.match(code)
    issue_id = resp.json()["data"]["id"]
    async with test_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT workspace_id FROM issues WHERE id = :id"),
                {"id": issue_id},
            )
        ).fetchone()
    assert row is not None and row[0] == user["workspaceId"]


@pytest.mark.asyncio
async def test_api_sole_writable_no_header_binds(test_client: AsyncClient, test_engine: AsyncEngine):
    user = await _register(test_client, "e98sole")
    ws = (
        await test_client.get(
            f"/api/workspaces/{user['workspaceId']}",
            headers=_auth(user["token"]),
        )
    ).json()["data"]
    key = ws["issueKey"]
    resp = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"]),  # no X-Workspace-Id
        json={"title": "E98 sole bind", "type": "bug"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert KEY_N.match(data["issue_code"]), data["issue_code"]
    assert data["issue_code"].startswith(f"{key}-")
    async with test_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT workspace_id FROM issues WHERE id = :id"),
                {"id": data["id"]},
            )
        ).fetchone()
    assert row is not None and row[0] == user["workspaceId"]


@pytest.mark.asyncio
async def test_api_multi_writable_no_header_400(test_client: AsyncClient):
    user = await _register(test_client, "e98multi")
    # second writable workspace owned by same user
    key = f"M{uuid.uuid4().hex[:4].upper()}"
    created = await test_client.post(
        "/api/workspaces",
        headers=_auth(user["token"]),
        json={"name": f"Extra {key}", "issueKey": key},
    )
    assert created.status_code == 200, created.text
    resp = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"]),
        json={"title": "E98 ambiguous", "type": "bug"},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json().get("detail") or resp.text
    assert "workspace_required" in str(detail) or "X-Workspace-Id" in str(detail)


@pytest.mark.asyncio
async def test_api_viewer_only_no_header_400(
    test_client: AsyncClient, test_engine: AsyncEngine
):
    owner = await _register(test_client, "e98own")
    viewer = await _register(test_client, "e98view")
    # demote viewer's sole WS membership to viewer via SQL, and add as viewer on owner's WS
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE workspace_members SET role = 'viewer' "
                "WHERE user_id = :uid AND workspace_id = :wid"
            ),
            {"uid": viewer["userId"], "wid": viewer["workspaceId"]},
        )
        await conn.execute(
            text(
                "INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at) "
                "VALUES (:id, :wid, :uid, 'viewer', NOW())"
            ),
            {
                "id": str(uuid.uuid4()),
                "wid": owner["workspaceId"],
                "uid": viewer["userId"],
            },
        )
    resp = await test_client.post(
        "/api/issues",
        headers=_auth(viewer["token"]),
        json={"title": "E98 viewer blocked", "type": "bug"},
    )
    assert resp.status_code == 400, resp.text
    detail = str(resp.json().get("detail") or resp.text)
    assert "workspace_required" in detail or "X-Workspace-Id" in detail


@pytest.mark.asyncio
async def test_resolve_helper_sole_and_errors(test_engine: AsyncEngine):
    async with test_engine.begin() as conn:
        # use nested session pattern carefully — prefer API for state, unit for helper
        pass

    # Lightweight: instantiate against a fresh session from engine
    from opentask.repositories.base import SessionCreator

    async with SessionCreator() as session:
        # empty user → zero writable
        fake_uid = str(uuid.uuid4())
        with pytest.raises(WorkspaceRequiredError):
            await resolve_workspace_for_issue_create(session, fake_uid)

        # explicit wins without membership check here (caller validates membership)
        wid = str(uuid.uuid4())
        got = await resolve_workspace_for_issue_create(
            session, fake_uid, explicit_workspace_id=wid
        )
        assert got == wid


@pytest.mark.asyncio
async def test_legacy_by_code_still_works(
    test_client: AsyncClient, test_engine: AsyncEngine
):
    user = await _register(test_client, "e98leg")
    created = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "E98 legacy read", "type": "bug"},
    )
    assert created.status_code == 200, created.text
    issue_id = created.json()["data"]["id"]
    legacy = f"ISSUE2026-{uuid.uuid4().int % 100000 + 1}"
    async with test_engine.begin() as conn:
        await conn.execute(
            text("UPDATE issues SET legacy_issue_code = :legacy WHERE id = :id"),
            {"legacy": legacy, "id": issue_id},
        )
    resp = await test_client.get(
        f"/api/issues/{legacy}",
        params={"by_code": "true"},
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["id"] == issue_id


@pytest.mark.asyncio
async def test_generate_path_uses_for_update(test_client: AsyncClient):
    """Directed: source still uses SELECT … FOR UPDATE (SQLite/PG path)."""
    import inspect
    from opentask.services import issue_service as mod

    src = inspect.getsource(mod.IssueService._generate_issue_code)
    assert "with_for_update" in src
    assert "current_year" not in src
    assert "prefix_pattern" not in src
    assert "LIKE" not in src
    # docstring may mention removed ISSUE{year}; body must not allocate it
    body = src.split('"""', 2)[-1] if '"""' in src else src
    assert "ISSUE{" not in body or "removed" in src
    assert "datetime.now" not in src


@pytest.mark.asyncio
async def test_sequential_key_n_same_ws(test_client: AsyncClient):
    user = await _register(test_client, "e98seq")
    ws = (
        await test_client.get(
            f"/api/workspaces/{user['workspaceId']}",
            headers=_auth(user["token"]),
        )
    ).json()["data"]
    key = ws["issueKey"]
    codes = []
    for i in range(3):
        r = await test_client.post(
            "/api/issues",
            headers=_auth(user["token"], user["workspaceId"]),
            json={"title": f"seq {i}", "type": "bug"},
        )
        assert r.status_code == 200, r.text
        codes.append(r.json()["data"]["issue_code"])
    assert codes == [f"{key}-1", f"{key}-2", f"{key}-3"]


def test_workspace_required_detail_mentions_key_n():
    assert "KEY-N" in WORKSPACE_REQUIRED_DETAIL
    assert "X-Workspace-Id" in WORKSPACE_REQUIRED_DETAIL
    assert "ISSUE" in WORKSPACE_REQUIRED_DETAIL


def test_create_surfaces_call_resolver():
    """Jira / Tasks / collection / POST issues wire resolve_workspace_for_issue_create."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "opentask"
    files = [
        root / "api/issue/router.py",
        root / "api/jira/router.py",
        root / "api/tasks/router.py",
        root / "services/issue_collection_service.py",
    ]
    for f in files:
        src = f.read_text()
        assert "resolve_workspace_for_issue_create" in src, f
        assert "WorkspaceRequiredError" in src, f
