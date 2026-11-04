"""Saved Views：个人 + E7-S2 工作区共享权限矩阵"""
from __future__ import annotations

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


async def _add_member(
    client: AsyncClient, owner: dict, member: dict, role: str = "member"
):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


def _ids(rows: list[dict]) -> set[str]:
    return {r["id"] for r in rows}


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
    assert body.get("isShared") is False
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
    data = listed.json()["data"]
    assert any(r["id"] == view_id for r in data["rows"])
    assert any(r["id"] == view_id for r in data["personal"])
    assert view_id not in _ids(data["shared"])

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
    data = b_list.json()["data"]
    assert a_id not in _ids(data["rows"])
    assert a_id not in _ids(data["personal"])
    assert a_id not in _ids(data["shared"])

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
    ids = _ids(listed.json()["data"]["rows"])
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


# ----- E7-S2 shared views -----


@pytest.mark.asyncio
async def test_create_shared_view_listed_for_other_member(test_client: AsyncClient):
    a = await _register(test_client, "sv_sh_a")
    b = await _register(test_client, "sv_sh_b")
    await _add_member(test_client, a, b)

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={
            "name": "团队开放",
            "filter": {"status": "open"},
            "is_shared": True,
            "display": {"view_mode": "list", "group_by": "label"},
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()["data"]
    assert body["isShared"] is True
    assert body["isFavorite"] is False
    view_id = body["id"]

    a_list = await test_client.get(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
    )
    assert a_list.status_code == 200, a_list.text
    a_data = a_list.json()["data"]
    assert view_id in _ids(a_data["shared"])
    assert view_id not in _ids(a_data["personal"])
    assert view_id in _ids(a_data["rows"])

    b_list = await test_client.get(
        "/api/saved-views",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert b_list.status_code == 200, b_list.text
    b_data = b_list.json()["data"]
    assert view_id in _ids(b_data["shared"])
    assert view_id not in _ids(b_data["personal"])

    b_get = await test_client.get(
        f"/api/saved-views/{view_id}",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert b_get.status_code == 200, b_get.text
    assert b_get.json()["data"]["isShared"] is True


@pytest.mark.asyncio
async def test_list_personal_shared_isolation(test_client: AsyncClient):
    a = await _register(test_client, "sv_iso_a")
    b = await _register(test_client, "sv_iso_b")
    await _add_member(test_client, a, b)

    personal = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "A-personal", "filter": {"type": "bug"}, "is_shared": False},
    )
    shared = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "A-shared", "filter": {"type": "feature"}, "is_shared": True},
    )
    b_personal = await test_client.post(
        "/api/saved-views",
        headers=_auth(b["token"], a["workspaceId"]),
        json={"name": "B-personal", "filter": {"priority": "high"}},
    )
    assert personal.status_code == 200 and shared.status_code == 200
    assert b_personal.status_code == 200
    p_id = personal.json()["data"]["id"]
    s_id = shared.json()["data"]["id"]
    bp_id = b_personal.json()["data"]["id"]

    b_list = await test_client.get(
        "/api/saved-views",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    data = b_list.json()["data"]
    assert p_id not in _ids(data["personal"]) and p_id not in _ids(data["shared"])
    assert s_id in _ids(data["shared"]) and s_id not in _ids(data["personal"])
    assert bp_id in _ids(data["personal"]) and bp_id not in _ids(data["shared"])


@pytest.mark.asyncio
async def test_member_cannot_patch_others_personal(test_client: AsyncClient):
    a = await _register(test_client, "sv_op_a")
    b = await _register(test_client, "sv_op_b")
    await _add_member(test_client, a, b)

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "secret", "filter": {}},
    )
    view_id = created.json()["data"]["id"]

    patched = await test_client.patch(
        f"/api/saved-views/{view_id}",
        headers=_auth(b["token"], a["workspaceId"]),
        json={"name": "hacked"},
    )
    assert patched.status_code == 404

    deleted = await test_client.delete(
        f"/api/saved-views/{view_id}",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert deleted.status_code == 404


@pytest.mark.asyncio
async def test_member_cannot_patch_shared_unless_creator(test_client: AsyncClient):
    a = await _register(test_client, "sv_cr_a")
    b = await _register(test_client, "sv_cr_b")
    await _add_member(test_client, a, b)

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "shared-by-a", "filter": {"tab": "open"}, "is_shared": True},
    )
    view_id = created.json()["data"]["id"]

    denied = await test_client.patch(
        f"/api/saved-views/{view_id}",
        headers=_auth(b["token"], a["workspaceId"]),
        json={"name": "nope"},
    )
    assert denied.status_code == 403

    ok = await test_client.patch(
        f"/api/saved-views/{view_id}",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "shared-renamed", "filter": {"tab": "all"}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["name"] == "shared-renamed"


@pytest.mark.asyncio
async def test_workspace_owner_can_patch_shared_created_by_member(
    test_client: AsyncClient,
):
    owner = await _register(test_client, "sv_own")
    member = await _register(test_client, "sv_mem")
    await _add_member(test_client, owner, member, role="member")

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"name": "member-shared", "filter": {"status": "open"}, "is_shared": True},
    )
    assert created.status_code == 200, created.text
    view_id = created.json()["data"]["id"]

    patched = await test_client.patch(
        f"/api/saved-views/{view_id}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "owner-fixed"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "owner-fixed"


@pytest.mark.asyncio
async def test_save_as_shared_creates_personal_copy(test_client: AsyncClient):
    a = await _register(test_client, "sv_sa_a")
    b = await _register(test_client, "sv_sa_b")
    await _add_member(test_client, a, b)

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={
            "name": "Team Bugs",
            "filter": {"type": "bug", "priority": "high"},
            "sort": {"sort_by": "priority", "sort_order": "desc"},
            "display": {"view_mode": "board", "group_by": "status"},
            "is_shared": True,
        },
    )
    assert created.status_code == 200, created.text
    src = created.json()["data"]
    view_id = src["id"]

    save_as = await test_client.post(
        f"/api/saved-views/{view_id}/save-as",
        headers=_auth(b["token"], a["workspaceId"]),
        json={"name": "My copy of Team Bugs"},
    )
    assert save_as.status_code == 200, save_as.text
    copy = save_as.json()["data"]
    assert copy["id"] != view_id
    assert copy["isShared"] is False
    assert copy["ownerUserId"] == b["userId"]
    assert copy["name"] == "My copy of Team Bugs"
    assert copy["filter"] == src["filter"]
    assert copy["sort"] == src["sort"]
    assert copy["display"] == src["display"]
    assert copy["isFavorite"] is False

    # original unchanged
    still = await test_client.get(
        f"/api/saved-views/{view_id}",
        headers=_auth(a["token"], a["workspaceId"]),
    )
    assert still.json()["data"]["isShared"] is True
    assert still.json()["data"]["name"] == "Team Bugs"

    b_list = await test_client.get(
        "/api/saved-views",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    data = b_list.json()["data"]
    assert copy["id"] in _ids(data["personal"])
    assert copy["id"] not in _ids(data["shared"])


@pytest.mark.asyncio
async def test_viewer_can_get_shared_cannot_create_or_save_as(test_client: AsyncClient):
    owner = await _register(test_client, "sv_v_own")
    viewer = await _register(test_client, "sv_v_view")
    await _add_member(test_client, owner, viewer, role="viewer")

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "visible", "filter": {}, "is_shared": True},
    )
    assert created.status_code == 200, created.text
    view_id = created.json()["data"]["id"]

    listed = await test_client.get(
        "/api/saved-views",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    assert view_id in _ids(listed.json()["data"]["shared"])

    got = await test_client.get(
        f"/api/saved-views/{view_id}",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert got.status_code == 200

    denied_create = await test_client.post(
        "/api/saved-views",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"name": "nope", "filter": {}, "is_shared": True},
    )
    assert denied_create.status_code == 403

    denied_save = await test_client.post(
        f"/api/saved-views/{view_id}/save-as",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={},
    )
    assert denied_save.status_code == 403


@pytest.mark.asyncio
async def test_favorite_rejected_on_shared_view(test_client: AsyncClient):
    user = await _register(test_client, "sv_fav")
    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "shared-no-star", "filter": {}, "is_shared": True},
    )
    assert created.status_code == 200, created.text
    view_id = created.json()["data"]["id"]
    assert created.json()["data"]["isFavorite"] is False

    fav = await test_client.post(
        f"/api/saved-views/{view_id}/favorite",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"is_favorite": True},
    )
    assert fav.status_code == 403

    # personal still works
    personal = await test_client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "mine", "filter": {}, "is_shared": False},
    )
    pid = personal.json()["data"]["id"]
    ok = await test_client.post(
        f"/api/saved-views/{pid}/favorite",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"is_favorite": True},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["isFavorite"] is True


@pytest.mark.asyncio
async def test_shared_cross_workspace_invisible(test_client: AsyncClient):
    a = await _register(test_client, "sv_x_a")
    b = await _register(test_client, "sv_x_b")

    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "ws-a-shared", "filter": {}, "is_shared": True},
    )
    assert created.status_code == 200, created.text
    view_id = created.json()["data"]["id"]

    # B not a member of A's workspace
    forbidden_list = await test_client.get(
        "/api/saved-views",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert forbidden_list.status_code == 403

    # B's own workspace must not see A's view
    b_list = await test_client.get(
        "/api/saved-views",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert b_list.status_code == 200, b_list.text
    assert view_id not in _ids(b_list.json()["data"]["rows"])
    assert view_id not in _ids(b_list.json()["data"]["shared"])

    missing = await test_client.get(
        f"/api/saved-views/{view_id}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert missing.status_code == 404
