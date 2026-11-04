"""E4-S1：个人 Saved Views（筛选/排序配置）"""
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "sv"):
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


async def _add_member(client: AsyncClient, owner: dict, member: dict):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": "member"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_create_and_list_saved_views(test_client: AsyncClient):
    user = await _register(test_client, "sv_c")
    payload = {
        "name": "我的开放缺陷",
        "filter": {"status": "open", "type": "bug", "priority": "high"},
        "sort": {"sort_by": "created_at", "sort_order": "desc"},
        "is_favorite": True,
    }
    create = await test_client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json=payload,
    )
    assert create.status_code == 200, create.text
    body = create.json()["data"]
    assert body["name"] == "我的开放缺陷"
    assert body["isFavorite"] is True
    assert body["filter"]["type"] == "bug"
    assert body["sort"]["sort_by"] == "created_at"
    assert body["ownerUserId"] == user["userId"]
    assert body["workspaceId"] == user["workspaceId"]
    view_id = body["id"]

    listed = await test_client.get(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert any(r["id"] == view_id for r in rows)

    one = await test_client.get(
        f"/api/saved-views/{view_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.status_code == 200, one.text
    assert one.json()["data"]["id"] == view_id


@pytest.mark.asyncio
async def test_saved_views_isolation_between_users(test_client: AsyncClient):
    a = await _register(test_client, "sv_a")
    b = await _register(test_client, "sv_b")
    await _add_member(test_client, a, b)

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "A-only", "filter": {"status": "open"}},
    )
    assert created.status_code == 200, created.text
    a_id = created.json()["data"]["id"]

    b_list = await test_client.get(
        "/api/saved-views",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert b_list.status_code == 200, b_list.text
    b_ids = {r["id"] for r in b_list.json()["data"]["rows"]}
    assert a_id not in b_ids

    b_get = await test_client.get(
        f"/api/saved-views/{a_id}",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert b_get.status_code == 404


@pytest.mark.asyncio
async def test_update_and_favorite_saved_view(test_client: AsyncClient):
    user = await _register(test_client, "sv_u")
    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "tmp", "filter": {"priority": "low"}, "is_favorite": False},
    )
    assert created.status_code == 200, created.text
    view_id = created.json()["data"]["id"]

    patched = await test_client.patch(
        f"/api/saved-views/{view_id}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": "高优",
            "filter": {"priority": "urgent"},
            "is_favorite": True,
            "sort": {"sort_by": "priority", "sort_order": "asc"},
        },
    )
    assert patched.status_code == 200, patched.text
    data = patched.json()["data"]
    assert data["name"] == "高优"
    assert data["filter"]["priority"] == "urgent"
    assert data["isFavorite"] is True
    assert data["sort"]["sort_order"] == "asc"

    fav = await test_client.post(
        f"/api/saved-views/{view_id}/favorite",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"is_favorite": False},
    )
    assert fav.status_code == 200, fav.text
    assert fav.json()["data"]["isFavorite"] is False


@pytest.mark.asyncio
async def test_delete_saved_view(test_client: AsyncClient):
    user = await _register(test_client, "sv_d")
    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "to-delete", "filter": {}},
    )
    view_id = created.json()["data"]["id"]

    deleted = await test_client.delete(
        f"/api/saved-views/{view_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    listed = await test_client.get(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    ids = {r["id"] for r in listed.json()["data"]["rows"]}
    assert view_id not in ids

    gone = await test_client.get(
        f"/api/saved-views/{view_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_saved_views_require_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "sv_h")
    missing = await test_client.get(
        "/api/saved-views",
        headers=_auth(user["token"]),  # no workspace
    )
    assert missing.status_code == 400

    other = await _register(test_client, "sv_o")
    forbidden = await test_client.get(
        "/api/saved-views",
        headers=_auth(user["token"], other["workspaceId"]),
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_saved_view_display_group_by(test_client: AsyncClient):
    """E4-S2：display.group_by 可创建并 PATCH 往返。"""
    user = await _register(test_client, "sv_gb")
    create = await test_client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": "按优先级分组",
            "filter": {"tab": "open"},
            "display": {"view_mode": "list", "group_by": "priority"},
        },
    )
    assert create.status_code == 200, create.text
    body = create.json()["data"]
    assert body["display"]["group_by"] == "priority"
    view_id = body["id"]

    patched = await test_client.patch(
        f"/api/saved-views/{view_id}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"display": {"view_mode": "list", "group_by": "assignee"}},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["display"]["group_by"] == "assignee"

