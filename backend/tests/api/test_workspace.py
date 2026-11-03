"""Workspace API 与租户隔离测试（E3-S1）"""
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "u"):
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


@pytest.mark.asyncio
async def test_list_workspaces_includes_default(test_client: AsyncClient):
    user = await _register(test_client, "ws")
    resp = await test_client.get("/api/workspaces", headers=_auth(user["token"]))
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert len(rows) >= 1
    ids = {r["id"] for r in rows}
    assert user["workspaceId"] in ids


@pytest.mark.asyncio
async def test_create_workspace_and_project_isolation(test_client: AsyncClient):
    user = await _register(test_client, "iso")
    # 再建一个工作区
    create_ws = await test_client.post(
        "/api/workspaces",
        headers=_auth(user["token"]),
        json={"name": "Second WS", "slug": f"second-{uuid.uuid4().hex[:6]}"},
    )
    assert create_ws.status_code == 200, create_ws.text
    ws2 = create_ws.json()["data"]["id"]

    # 在 ws2 建项目
    pname = f"P-{uuid.uuid4().hex[:6]}"
    proj = await test_client.post(
        "/api/projects",
        headers=_auth(user["token"], ws2),
        json={"name": pname, "description": "in ws2"},
    )
    assert proj.status_code == 200, proj.text
    project = proj.json()["data"]
    assert project["name"] == pname

    # ws2 列表应能看到
    list2 = await test_client.get("/api/projects", headers=_auth(user["token"], ws2))
    assert list2.status_code == 200
    names2 = {p["name"] for p in list2.json()["data"]}
    assert pname in names2

    # 默认工作区列表不应看到 ws2 项目
    list1 = await test_client.get(
        "/api/projects", headers=_auth(user["token"], user["workspaceId"])
    )
    assert list1.status_code == 200
    names1 = {p["name"] for p in list1.json()["data"]}
    assert pname not in names1


@pytest.mark.asyncio
async def test_foreign_workspace_forbidden(test_client: AsyncClient):
    a = await _register(test_client, "a")
    b = await _register(test_client, "b")
    # A 用 B 的 workspace 头
    resp = await test_client.get(
        "/api/projects",
        headers=_auth(a["token"], b["workspaceId"]),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_issue_cross_workspace_isolation(test_client: AsyncClient):
    user = await _register(test_client, "iss")
    # 第二工作区
    ws2 = (
        await test_client.post(
            "/api/workspaces",
            headers=_auth(user["token"]),
            json={"name": "Issue WS2"},
        )
    ).json()["data"]["id"]

    # 在默认区建 issue
    issue1 = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "Issue in WS1", "type": "bug"},
    )
    assert issue1.status_code == 200, issue1.text

    # 在 ws2 建 issue
    issue2 = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], ws2),
        json={"title": "Issue in WS2", "type": "bug"},
    )
    assert issue2.status_code == 200, issue2.text

    list1 = await test_client.get(
        "/api/issues", headers=_auth(user["token"], user["workspaceId"])
    )
    assert list1.status_code == 200
    titles1 = {row["title"] for row in list1.json()["data"]["rows"]}
    assert "Issue in WS1" in titles1
    assert "Issue in WS2" not in titles1

    list2 = await test_client.get("/api/issues", headers=_auth(user["token"], ws2))
    titles2 = {row["title"] for row in list2.json()["data"]["rows"]}
    assert "Issue in WS2" in titles2
    assert "Issue in WS1" not in titles2


@pytest.mark.asyncio
async def test_owner_can_add_member(test_client: AsyncClient):
    owner = await _register(test_client, "own")
    other = await _register(test_client, "mem")
    resp = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": other["userId"], "role": "member"},
    )
    assert resp.status_code == 200, resp.text
    # other 现在可以访问
    ok = await test_client.get(
        "/api/projects",
        headers=_auth(other["token"], owner["workspaceId"]),
    )
    assert ok.status_code == 200
