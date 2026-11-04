"""E3-S2：Issue 看板 position 排序与 board/move"""
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "b"):
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


@pytest.mark.asyncio
async def test_list_sort_by_position(test_client: AsyncClient):
    user = await _register(test_client, "pos")
    a = await _create_issue(test_client, user, "pos-a", position=2)
    b = await _create_issue(test_client, user, "pos-b", position=0)
    c = await _create_issue(test_client, user, "pos-c", position=1)

    resp = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"sort_by": "position", "sort_order": "asc", "page_size": 50},
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]["rows"]
    ids = [r["id"] for r in rows if r["id"] in {a["id"], b["id"], c["id"]}]
    assert ids == [b["id"], c["id"], a["id"]]


@pytest.mark.asyncio
async def test_board_move_updates_status_and_position(test_client: AsyncClient):
    user = await _register(test_client, "mv")
    issue = await _create_issue(test_client, user, "move-me", position=0, status="open")

    resp = await test_client.post(
        "/api/issues/board/move",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "issue_id": issue["id"],
            "status": "in_progress",
            "position": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "in_progress"
    assert data["position"] == 3

    got = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200
    body = got.json()["data"]
    assert body["status"] == "in_progress"
    assert body["position"] == 3


@pytest.mark.asyncio
async def test_board_move_ordered_ids_rewrites_positions(test_client: AsyncClient):
    user = await _register(test_client, "ord")
    i1 = await _create_issue(test_client, user, "o1", position=0, status="open")
    i2 = await _create_issue(test_client, user, "o2", position=1, status="open")
    i3 = await _create_issue(test_client, user, "o3", position=2, status="open")

    # 把 i3 拖到列首，ordered = [i3, i1, i2]
    resp = await test_client.post(
        "/api/issues/board/move",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "issue_id": i3["id"],
            "status": "open",
            "position": 0,
            "ordered_ids": [i3["id"], i1["id"], i2["id"]],
        },
    )
    assert resp.status_code == 200, resp.text

    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"sort_by": "position", "sort_order": "asc", "page_size": 50, "status": "open"},
    )
    assert listed.status_code == 200
    rows = listed.json()["data"]["rows"]
    subset = [r for r in rows if r["id"] in {i1["id"], i2["id"], i3["id"]}]
    assert [r["id"] for r in subset] == [i3["id"], i1["id"], i2["id"]]
    assert [r["position"] for r in subset] == [0, 1, 2]


@pytest.mark.asyncio
async def test_board_move_cross_workspace_forbidden(test_client: AsyncClient):
    user = await _register(test_client, "xw")
    issue = await _create_issue(test_client, user, "ws1-issue", position=0)

    # 再建工作区
    ws2 = await test_client.post(
        "/api/workspaces",
        headers=_auth(user["token"]),
        json={"name": f"WS2-{uuid.uuid4().hex[:6]}"},
    )
    assert ws2.status_code == 200, ws2.text
    ws2_id = ws2.json()["data"]["id"]

    # 用 WS2 头移动 WS1 的 issue → 403
    resp = await test_client.post(
        "/api/issues/board/move",
        headers=_auth(user["token"], ws2_id),
        json={"issue_id": issue["id"], "status": "closed", "position": 0},
    )
    assert resp.status_code == 403, resp.text

    # 确认未改写
    got = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.json()["data"]["status"] == "open"


@pytest.mark.asyncio
async def test_put_still_updates_status_and_position(test_client: AsyncClient):
    user = await _register(test_client, "put")
    issue = await _create_issue(test_client, user, "put-me", position=1)

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": "feedback", "position": 9},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "feedback"
    assert data["position"] == 9
