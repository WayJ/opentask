"""E70: childProgress on issue detail / list include / children endpoint."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e70"):
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


def _auth(token: str, workspace_id: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h


async def _issue(client, user, title="E70", **extra):
    body = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        "reporter_id": user["userId"],
        **extra,
    }
    r = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest.mark.asyncio
async def test_detail_default_child_progress_mixed(test_client: AsyncClient):
    user = await _register(test_client, "mix")
    parent = await _issue(test_client, user, "parent")
    for title, st in [
        ("c1", "resolved"),
        ("c2", "resolved"),
        ("c3", "closed"),
        ("c4", "open"),
        ("c5", "in_progress"),
    ]:
        child = await _issue(test_client, user, title, parent_issue_id=parent["id"])
        if st != "open":
            ur = await test_client.put(
                f"/api/issues/{child['id']}",
                headers=_auth(user["token"], user["workspaceId"]),
                json={"status": st},
            )
            assert ur.status_code == 200, ur.text

    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 5
    assert cp["done"] == 3
    assert cp["open"] == 2
    assert cp["percent"] == 60


@pytest.mark.asyncio
async def test_detail_zero_children_percent_null(test_client: AsyncClient):
    user = await _register(test_client, "z")
    parent = await _issue(test_client, user, "lonely")
    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 0
    assert cp["done"] == 0
    assert cp["open"] == 0
    assert cp["percent"] is None


@pytest.mark.asyncio
async def test_soft_deleted_child_excluded(test_client: AsyncClient):
    user = await _register(test_client, "del")
    parent = await _issue(test_client, user, "p-del")
    live = await _issue(test_client, user, "live", parent_issue_id=parent["id"])
    gone = await _issue(test_client, user, "gone", parent_issue_id=parent["id"])
    dr = await test_client.delete(
        f"/api/issues/{gone['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert dr.status_code == 200, dr.text
    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 1
    assert live["id"]
    assert cp["percent"] == 0


@pytest.mark.asyncio
async def test_list_without_include_omits_key(test_client: AsyncClient):
    user = await _register(test_client, "li0")
    parent = await _issue(test_client, user, "p-li0")
    await _issue(test_client, user, "c", parent_issue_id=parent["id"])
    lst = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"page_size": 50},
    )
    assert lst.status_code == 200
    rows = lst.json()["data"]["rows"]
    row = next(r for r in rows if r["id"] == parent["id"])
    assert "childProgress" not in row


@pytest.mark.asyncio
async def test_list_include_matches_detail(test_client: AsyncClient):
    user = await _register(test_client, "li1")
    parent = await _issue(test_client, user, "p-li1")
    c = await _issue(test_client, user, "c-done", parent_issue_id=parent["id"])
    await test_client.put(
        f"/api/issues/{c['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": "resolved"},
    )
    detail = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    dcp = detail.json()["data"]["childProgress"]
    lst = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"include": "childProgress", "page_size": 50},
    )
    row = next(r for r in lst.json()["data"]["rows"] if r["id"] == parent["id"])
    assert row["childProgress"]["total"] == dcp["total"]
    assert row["childProgress"]["done"] == dcp["done"]
    assert row["childProgress"]["percent"] == dcp["percent"]


@pytest.mark.asyncio
async def test_children_endpoint_embeds_progress(test_client: AsyncClient):
    user = await _register(test_client, "ch")
    parent = await _issue(test_client, user, "p-ch")
    await _issue(test_client, user, "c1", parent_issue_id=parent["id"])
    r = await test_client.get(
        f"/api/issues/{parent['id']}/children",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] == 1
    assert data["childProgress"]["total"] == 1
    assert data["childProgress"]["percent"] == 0


@pytest.mark.asyncio
async def test_grandchild_not_counted(test_client: AsyncClient):
    user = await _register(test_client, "gc")
    parent = await _issue(test_client, user, "p-gc")
    child = await _issue(test_client, user, "c-gc", parent_issue_id=parent["id"])
    await _issue(test_client, user, "gc1", parent_issue_id=child["id"])
    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 1


@pytest.mark.asyncio
async def test_detail_read_no_new_webhook(test_client: AsyncClient, monkeypatch):
    fired: list = []

    async def _spy(*args, **kwargs):
        fired.append((args, kwargs))

    monkeypatch.setattr(
        "opentask.services.issue_service.fire_webhooks",
        AsyncMock(side_effect=_spy),
    )
    user = await _register(test_client, "wh")
    parent = await _issue(test_client, user, "p-wh")
    await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    before = len(fired)
    await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert len(fired) == before
