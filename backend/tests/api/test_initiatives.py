"""E10-S1：Initiative CRUD + M2M Projects (Issue/Project axis only)"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ini"):
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


async def _add_member(client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


async def _create_project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"Proj-{uuid.uuid4().hex[:6]}", "description": "ini"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_crud_initiative(test_client: AsyncClient):
    user = await _register(test_client, "ini_crud")
    h = _auth(user["token"], user["workspaceId"])

    created = await test_client.post(
        "/api/initiatives",
        headers=h,
        json={
            "name": "Q4 增长",
            "description": "跨项目目标",
            "status": "planned",
            "sortOrder": 1,
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["name"] == "Q4 增长"
    assert row["status"] == "planned"
    assert row["workspaceId"] == user["workspaceId"]
    assert row["projectIds"] == []
    iid = row["id"]

    listed = await test_client.get("/api/initiatives", headers=h)
    assert listed.status_code == 200, listed.text
    data = listed.json()["data"]
    assert data["total"] >= 1
    assert any(r["id"] == iid for r in data["rows"])

    got = await test_client.get(f"/api/initiatives/{iid}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["name"] == "Q4 增长"

    patched = await test_client.patch(
        f"/api/initiatives/{iid}",
        headers=h,
        json={"name": "Q4 增长 v2", "status": "active"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "Q4 增长 v2"
    assert patched.json()["data"]["status"] == "active"

    deleted = await test_client.delete(f"/api/initiatives/{iid}", headers=h)
    assert deleted.status_code == 200, deleted.text

    missing = await test_client.get(f"/api/initiatives/{iid}", headers=h)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_name_conflict(test_client: AsyncClient):
    user = await _register(test_client, "ini_dup")
    h = _auth(user["token"], user["workspaceId"])
    r1 = await test_client.post("/api/initiatives", headers=h, json={"name": "同名"})
    assert r1.status_code == 200, r1.text
    r2 = await test_client.post("/api/initiatives", headers=h, json={"name": "同名"})
    assert r2.status_code in (400, 409), r2.text


@pytest.mark.asyncio
async def test_viewer_read_ok_write_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "ini_own")
    viewer = await _register(test_client, "ini_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])

    created = await test_client.post("/api/initiatives", headers=oh, json={"name": "可见"})
    assert created.status_code == 200, created.text
    iid = created.json()["data"]["id"]

    listed = await test_client.get("/api/initiatives", headers=vh)
    assert listed.status_code == 200, listed.text

    forbidden = await test_client.post("/api/initiatives", headers=vh, json={"name": "不可写"})
    assert forbidden.status_code == 403, forbidden.text

    patch_forbidden = await test_client.patch(
        f"/api/initiatives/{iid}", headers=vh, json={"status": "canceled"}
    )
    assert patch_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "ini_a")
    b = await _register(test_client, "ini_b")
    created = await test_client.post(
        "/api/initiatives",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "仅 A"},
    )
    assert created.status_code == 200, created.text
    iid = created.json()["data"]["id"]

    other = await test_client.get(
        f"/api/initiatives/{iid}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_m2m_projects_same_ws(test_client: AsyncClient):
    user = await _register(test_client, "ini_m2m")
    h = _auth(user["token"], user["workspaceId"])
    p1 = await _create_project(test_client, user, "P1")
    p2 = await _create_project(test_client, user, "P2")

    created = await test_client.post(
        "/api/initiatives",
        headers=h,
        json={"name": "带项目", "projectIds": [p1["id"]]},
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert set(row["projectIds"]) == {p1["id"]}
    iid = row["id"]

    replaced = await test_client.put(
        f"/api/initiatives/{iid}/projects",
        headers=h,
        json={"projectIds": [p1["id"], p2["id"]]},
    )
    assert replaced.status_code == 200, replaced.text
    assert set(replaced.json()["data"]["projectIds"]) == {p1["id"], p2["id"]}

    detached = await test_client.delete(
        f"/api/initiatives/{iid}/projects/{p1['id']}",
        headers=h,
    )
    assert detached.status_code == 200, detached.text
    assert set(detached.json()["data"]["projectIds"]) == {p2["id"]}

    attached = await test_client.post(
        f"/api/initiatives/{iid}/projects/{p1['id']}",
        headers=h,
    )
    assert attached.status_code == 200, attached.text
    assert set(attached.json()["data"]["projectIds"]) == {p1["id"], p2["id"]}


@pytest.mark.asyncio
async def test_foreign_ws_project_rejected(test_client: AsyncClient):
    a = await _register(test_client, "ini_fa")
    b = await _register(test_client, "ini_fb")
    foreign = await _create_project(test_client, b, "Foreign")
    ah = _auth(a["token"], a["workspaceId"])

    created = await test_client.post(
        "/api/initiatives",
        headers=ah,
        json={"name": "拒外域", "projectIds": [foreign["id"]]},
    )
    assert created.status_code in (400, 404), created.text

    ok = await test_client.post("/api/initiatives", headers=ah, json={"name": "空链"})
    assert ok.status_code == 200, ok.text
    iid = ok.json()["data"]["id"]

    bad_put = await test_client.put(
        f"/api/initiatives/{iid}/projects",
        headers=ah,
        json={"projectIds": [foreign["id"]]},
    )
    assert bad_put.status_code in (400, 404), bad_put.text

    bad_post = await test_client.post(
        f"/api/initiatives/{iid}/projects/{foreign['id']}",
        headers=ah,
    )
    assert bad_post.status_code in (400, 404), bad_post.text


@pytest.mark.asyncio
async def test_invalid_status_rejected(test_client: AsyncClient):
    user = await _register(test_client, "ini_st")
    h = _auth(user["token"], user["workspaceId"])
    bad = await test_client.post(
        "/api/initiatives",
        headers=h,
        json={"name": "坏状态", "status": "shipping"},
    )
    assert bad.status_code == 422 or bad.status_code == 400, bad.text
