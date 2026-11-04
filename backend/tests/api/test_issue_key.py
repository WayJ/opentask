"""E12-S1: Workspace.issue_key + KEY-N allocation + dual-parse."""
from __future__ import annotations

import re
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _register(client: AsyncClient, prefix: str = "ik"):
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
async def test_register_workspace_has_issue_key(test_client: AsyncClient):
    user = await _register(test_client, "ik_reg")
    resp = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200
    ws = resp.json()["data"]
    assert "issueKey" in ws
    assert re.fullmatch(r"[A-Z0-9]{2,6}", ws["issueKey"]), ws["issueKey"]


@pytest.mark.asyncio
async def test_create_issue_gets_key_n(test_client: AsyncClient):
    user = await _register(test_client, "ik_c")
    ws = (
        await test_client.get(
            f"/api/workspaces/{user['workspaceId']}",
            headers=_auth(user["token"]),
        )
    ).json()["data"]
    key = ws["issueKey"]
    a = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "First", "type": "bug"},
    )
    assert a.status_code == 200, a.text
    assert a.json()["data"]["issue_code"] == f"{key}-1"
    b = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "Second", "type": "bug"},
    )
    assert b.status_code == 200, b.text
    assert b.json()["data"]["issue_code"] == f"{key}-2"


@pytest.mark.asyncio
async def test_patch_issue_key_only_affects_new(test_client: AsyncClient):
    user = await _register(test_client, "ik_p")
    first = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "Old", "type": "feature"},
    )
    assert first.status_code == 200, first.text
    old_code = first.json()["data"]["issue_code"]
    issue_id = first.json()["data"]["id"]
    new_key = f"Z{uuid.uuid4().hex[:4].upper()}"
    patch = await test_client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
        json={"issueKey": new_key},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["data"]["issueKey"] == new_key
    got = await test_client.get(
        f"/api/issues/{issue_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200
    assert got.json()["data"]["issue_code"] == old_code
    nxt = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "New", "type": "feature"},
    )
    assert nxt.status_code == 200, nxt.text
    assert nxt.json()["data"]["issue_code"].startswith(f"{new_key}-")


@pytest.mark.asyncio
async def test_by_code_resolves_key_n_in_workspace(test_client: AsyncClient):
    user = await _register(test_client, "ik_bc")
    created = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "ByCode", "type": "bug"},
    )
    assert created.status_code == 200, created.text
    code = created.json()["data"]["issue_code"]
    resp = await test_client.get(
        f"/api/issues/{code}",
        params={"by_code": "true"},
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["issue_code"] == code


@pytest.mark.asyncio
async def test_by_code_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "ik_a")
    b = await _register(test_client, "ik_b")
    created = await test_client.post(
        "/api/issues",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"title": "Secret", "type": "bug"},
    )
    assert created.status_code == 200, created.text
    code = created.json()["data"]["issue_code"]
    resp = await test_client.get(
        f"/api/issues/{code}",
        params={"by_code": "true"},
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_by_code_matches_legacy_issue_code(
    test_client: AsyncClient, test_engine: AsyncEngine
):
    user = await _register(test_client, "ik_lg")
    created = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "Legacy", "type": "bug"},
    )
    assert created.status_code == 200, created.text
    issue_id = created.json()["data"]["id"]
    legacy = f"ISSUE2026-{uuid.uuid4().int % 100000 + 1}"
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE issues SET legacy_issue_code = :legacy WHERE id = :id"
            ),
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
async def test_invalid_issue_key_rejected(test_client: AsyncClient):
    user = await _register(test_client, "ik_bad")
    resp = await test_client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
        json={"issueKey": "x"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_missing_legacy_by_code_404(test_client: AsyncClient):
    user = await _register(test_client, "ik_miss")
    resp = await test_client.get(
        "/api/issues/ISSUE2099-999999",
        params={"by_code": "true"},
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 404
