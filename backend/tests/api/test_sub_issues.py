"""E4-S3：一等公民子 Issue（parent_issue_id）"""
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "sub"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "username": uname,
        "password": password,
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra):
    body = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        "reporter_id": user["userId"],
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_second_workspace(client: AsyncClient, user: dict) -> str:
    resp = await client.post(
        "/api/workspaces",
        headers=_auth(user["token"]),
        json={"name": f"ws-{uuid.uuid4().hex[:6]}", "slug": f"ws-{uuid.uuid4().hex[:8]}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_child_issue_with_parent(test_client: AsyncClient):
    user = await _register(test_client, "p")
    parent = await _create_issue(test_client, user, "parent-issue")
    child = await _create_issue(
        test_client, user, "child-issue", parent_issue_id=parent["id"]
    )
    assert child["parent_issue_id"] == parent["id"]
    assert child["title"] == "child-issue"


@pytest.mark.asyncio
async def test_get_and_list_expose_parent_and_children(test_client: AsyncClient):
    user = await _register(test_client, "g")
    parent = await _create_issue(test_client, user, "parent-g")
    child = await _create_issue(
        test_client, user, "child-g", parent_issue_id=parent["id"]
    )

    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    pdata = got.json()["data"]
    assert pdata.get("parent_issue_id") in (None, "")
    children = pdata.get("children") or []
    assert any(c["id"] == child["id"] for c in children)
    c0 = next(c for c in children if c["id"] == child["id"])
    assert c0["title"] == "child-g"
    assert "status" in c0

    child_got = await test_client.get(
        f"/api/issues/{child['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert child_got.status_code == 200
    assert child_got.json()["data"]["parent_issue_id"] == parent["id"]

    ch_list = await test_client.get(
        f"/api/issues/{parent['id']}/children",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert ch_list.status_code == 200, ch_list.text
    rows = ch_list.json()["data"]["rows"]
    assert any(r["id"] == child["id"] for r in rows)

    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"page_size": 50},
    )
    assert listed.status_code == 200
    list_rows = listed.json()["data"]["rows"]
    child_row = next(r for r in list_rows if r["id"] == child["id"])
    assert child_row["parent_issue_id"] == parent["id"]


@pytest.mark.asyncio
async def test_reject_self_parent(test_client: AsyncClient):
    user = await _register(test_client, "self")
    issue = await _create_issue(test_client, user, "lonely")
    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"parent_issue_id": issue["id"]},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_reject_missing_parent(test_client: AsyncClient):
    user = await _register(test_client, "miss")
    resp = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "orphan-try",
            "type": "bug",
            "status": "open",
            "priority": "low",
            "reporter_id": user["userId"],
            "parent_issue_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_reject_cross_workspace_parent(test_client: AsyncClient):
    user = await _register(test_client, "xws")
    ws2 = await _create_second_workspace(test_client, user)

    # parent in ws2
    parent_resp = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], ws2),
        json={
            "title": "parent-ws2",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
        },
    )
    assert parent_resp.status_code == 200, parent_resp.text
    parent_id = parent_resp.json()["data"]["id"]

    # child attempt in default workspace with ws2 parent
    bad = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "child-ws1",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "parent_issue_id": parent_id,
        },
    )
    assert bad.status_code == 400, bad.text


@pytest.mark.asyncio
async def test_child_not_listed_in_other_workspace(test_client: AsyncClient):
    user = await _register(test_client, "iso")
    parent = await _create_issue(test_client, user, "iso-parent")
    child = await _create_issue(
        test_client, user, "iso-child", parent_issue_id=parent["id"]
    )
    ws2 = await _create_second_workspace(test_client, user)

    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], ws2),
        params={"page_size": 50},
    )
    assert listed.status_code == 200
    ids = {r["id"] for r in listed.json()["data"]["rows"]}
    assert child["id"] not in ids
    assert parent["id"] not in ids


@pytest.mark.asyncio
async def test_reject_cycle_parent(test_client: AsyncClient):
    user = await _register(test_client, "cyc")
    a = await _create_issue(test_client, user, "cyc-a")
    b = await _create_issue(test_client, user, "cyc-b", parent_issue_id=a["id"])
    # try make a.parent = b → cycle
    resp = await test_client.put(
        f"/api/issues/{a['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"parent_issue_id": b["id"]},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_clear_parent_with_null(test_client: AsyncClient):
    user = await _register(test_client, "clr")
    parent = await _create_issue(test_client, user, "clr-parent")
    child = await _create_issue(
        test_client, user, "clr-child", parent_issue_id=parent["id"]
    )
    resp = await test_client.put(
        f"/api/issues/{child['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"parent_issue_id": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["parent_issue_id"] is None
