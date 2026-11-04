"""E8-S3：Sidebar Favorites（独立于 Saved View is_favorite）"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "fav"):
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
        json={"name": name or f"FavProj-{uuid.uuid4().hex[:6]}", "description": "fav"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra) -> dict:
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


async def _create_saved_view(
    client: AsyncClient, user: dict, name: str = "My View", **extra
) -> dict:
    resp = await client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "filter": {"status": "open"}, **extra},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_pin_project_list_and_idempotent(test_client: AsyncClient):
    user = await _register(test_client, "fav_p")
    project = await _create_project(test_client, user, "Pinned Proj")

    pin = await test_client.post(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target_type": "project", "target_id": project["id"]},
    )
    assert pin.status_code == 200, pin.text
    row = pin.json()["data"]
    assert row["targetType"] == "project"
    assert row["targetId"] == project["id"]
    assert row["userId"] == user["userId"]
    assert row["workspaceId"] == user["workspaceId"]
    assert row["target"]["name"] == "Pinned Proj"
    assert row["target"]["type"] == "project"
    fav_id = row["id"]

    pin2 = await test_client.post(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target_type": "project", "target_id": project["id"]},
    )
    assert pin2.status_code == 200, pin2.text
    assert pin2.json()["data"]["id"] == fav_id

    listed = await test_client.get(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    data = listed.json()["data"]
    assert data["total"] == 1
    assert data["rows"][0]["id"] == fav_id
    assert data["rows"][0]["target"]["name"] == "Pinned Proj"


@pytest.mark.asyncio
async def test_pin_project_upserts_watcher_unpin_keeps_watcher(test_client: AsyncClient):
    owner = await _register(test_client, "fav_ow")
    member = await _register(test_client, "fav_mw")
    await _add_member(test_client, owner, member)
    project = await _create_project(test_client, owner)

    # member not watching yet
    before = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert before.status_code == 200
    assert all(r["user_id"] != member["userId"] for r in before.json()["data"])

    pin = await test_client.post(
        "/api/favorites",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"target_type": "project", "target_id": project["id"]},
    )
    assert pin.status_code == 200, pin.text
    fav_id = pin.json()["data"]["id"]

    watchers = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert any(r["user_id"] == member["userId"] for r in watchers.json()["data"])

    deleted = await test_client.delete(
        f"/api/favorites/{fav_id}",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    watchers2 = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    # unpin must NOT unwatch
    assert any(r["user_id"] == member["userId"] for r in watchers2.json()["data"])


@pytest.mark.asyncio
async def test_pin_issue_and_saved_view_with_summaries(test_client: AsyncClient):
    user = await _register(test_client, "fav_is")
    issue = await _create_issue(test_client, user, "Fav Issue Title")
    view = await _create_saved_view(test_client, user, "Sidebar View", is_favorite=False)

    pin_issue = await test_client.post(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target_type": "issue", "target_id": issue["id"]},
    )
    assert pin_issue.status_code == 200, pin_issue.text
    issue_row = pin_issue.json()["data"]
    assert issue_row["targetType"] == "issue"
    assert issue_row["target"]["name"] == "Fav Issue Title"
    assert issue_row["target"].get("code") == issue["issue_code"]

    pin_view = await test_client.post(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target_type": "saved_view", "target_id": view["id"]},
    )
    assert pin_view.status_code == 200, pin_view.text
    view_row = pin_view.json()["data"]
    assert view_row["targetType"] == "saved_view"
    assert view_row["target"]["name"] == "Sidebar View"

    # Sidebar pin must NOT flip Saved View star
    one = await test_client.get(
        f"/api/saved-views/{view['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.status_code == 200
    assert one.json()["data"]["isFavorite"] is False


@pytest.mark.asyncio
async def test_favorites_personal_isolation(test_client: AsyncClient):
    owner = await _register(test_client, "fav_iso_o")
    member = await _register(test_client, "fav_iso_m")
    await _add_member(test_client, owner, member)
    project = await _create_project(test_client, owner)

    pin = await test_client.post(
        "/api/favorites",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"target_type": "project", "target_id": project["id"]},
    )
    assert pin.status_code == 200, pin.text
    fav_id = pin.json()["data"]["id"]

    member_list = await test_client.get(
        "/api/favorites",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert member_list.status_code == 200
    assert all(r["id"] != fav_id for r in member_list.json()["data"]["rows"])

    steal = await test_client.delete(
        f"/api/favorites/{fav_id}",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert steal.status_code == 404


@pytest.mark.asyncio
async def test_favorites_invalid_target_and_type(test_client: AsyncClient):
    user = await _register(test_client, "fav_bad")

    bad_type = await test_client.post(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target_type": "cycle", "target_id": str(uuid.uuid4())},
    )
    assert bad_type.status_code == 400

    missing = await test_client.post(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target_type": "project", "target_id": str(uuid.uuid4())},
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_favorites_cross_workspace_target_404(test_client: AsyncClient):
    a = await _register(test_client, "fav_xa")
    b = await _register(test_client, "fav_xb")
    project_b = await _create_project(test_client, b)

    pin = await test_client.post(
        "/api/favorites",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"target_type": "project", "target_id": project_b["id"]},
    )
    assert pin.status_code == 404


@pytest.mark.asyncio
async def test_favorites_reorder_by_ordered_ids(test_client: AsyncClient):
    user = await _register(test_client, "fav_ord")
    p1 = await _create_project(test_client, user, "A")
    p2 = await _create_project(test_client, user, "B")
    p3 = await _create_project(test_client, user, "C")

    ids = []
    for p in (p1, p2, p3):
        resp = await test_client.post(
            "/api/favorites",
            headers=_auth(user["token"], user["workspaceId"]),
            json={"target_type": "project", "target_id": p["id"]},
        )
        assert resp.status_code == 200, resp.text
        ids.append(resp.json()["data"]["id"])

    # reverse order
    ordered = list(reversed(ids))
    reordered = await test_client.put(
        "/api/favorites/reorder",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"ordered_ids": ordered},
    )
    assert reordered.status_code == 200, reordered.text

    listed = await test_client.get(
        "/api/favorites",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200
    got = [r["id"] for r in listed.json()["data"]["rows"]]
    assert got == ordered


@pytest.mark.asyncio
async def test_favorites_require_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "fav_hdr")
    resp = await test_client.get(
        "/api/favorites",
        headers=_auth(user["token"]),  # no X-Workspace-Id
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_pin_initiative(test_client: AsyncClient):
    """E10-S2: Favorites target_type=initiative"""
    user = await _register(test_client, "fav_ini")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/initiatives",
        headers=h,
        json={"name": "钉住战略"},
    )
    assert created.status_code == 200, created.text
    iid = created.json()["data"]["id"]

    pinned = await test_client.post(
        "/api/favorites",
        headers=h,
        json={"target_type": "initiative", "target_id": iid},
    )
    assert pinned.status_code == 200, pinned.text
    row = pinned.json()["data"]
    assert row["targetType"] == "initiative"
    assert row["targetId"] == iid
    assert row["target"]["type"] == "initiative"
    assert row["target"]["name"] == "钉住战略"

    listed = await test_client.get("/api/favorites", headers=h)
    assert listed.status_code == 200
    types = {r["targetType"] for r in listed.json()["data"]["rows"]}
    assert "initiative" in types
