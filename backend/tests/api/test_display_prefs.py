"""E7-S3：个人 Issue Display prefs（与 Saved View display 隔离）"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "dp"):
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


SAMPLE_DISPLAY = {
    "view_mode": "board",
    "group_by": "none",
    "swimlane_by": "assignee",
    "hide_empty_lanes": True,
    "fields": {
        "assignee": True,
        "priority": False,
        "labels": True,
        "estimate_points": True,
        "due_date": False,
        "project": False,
        "cycle": False,
        "issue_code": True,
        "type": False,
    },
}


@pytest.mark.asyncio
async def test_get_prefs_null_when_absent(test_client: AsyncClient):
    user = await _register(test_client, "dp_g")
    resp = await test_client.get(
        "/api/display-prefs/issue",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["display"] is None


@pytest.mark.asyncio
async def test_put_and_get_roundtrip(test_client: AsyncClient):
    user = await _register(test_client, "dp_rt")
    put = await test_client.put(
        "/api/display-prefs/issue",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"display": SAMPLE_DISPLAY},
    )
    assert put.status_code == 200, put.text
    body = put.json()["data"]
    assert body["display"]["swimlane_by"] == "assignee"
    assert body["display"]["hide_empty_lanes"] is True
    assert body["display"]["fields"]["priority"] is False
    assert body["display"]["view_mode"] == "board"

    got = await test_client.get(
        "/api/display-prefs/issue",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    display = got.json()["data"]["display"]
    assert display["swimlane_by"] == "assignee"
    assert display["hide_empty_lanes"] is True
    assert display["fields"]["issue_code"] is True
    assert display["group_by"] == "none"


@pytest.mark.asyncio
async def test_put_upserts_same_user_ws(test_client: AsyncClient):
    user = await _register(test_client, "dp_up")
    await test_client.put(
        "/api/display-prefs/issue",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"display": {**SAMPLE_DISPLAY, "swimlane_by": "priority"}},
    )
    put2 = await test_client.put(
        "/api/display-prefs/issue",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"display": {**SAMPLE_DISPLAY, "swimlane_by": "type", "hide_empty_lanes": False}},
    )
    assert put2.status_code == 200, put2.text
    assert put2.json()["data"]["display"]["swimlane_by"] == "type"
    assert put2.json()["data"]["display"]["hide_empty_lanes"] is False

    got = await test_client.get(
        "/api/display-prefs/issue",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.json()["data"]["display"]["swimlane_by"] == "type"


@pytest.mark.asyncio
async def test_prefs_isolated_per_user(test_client: AsyncClient):
    a = await _register(test_client, "dp_a")
    b = await _register(test_client, "dp_b")
    await _add_member(test_client, a, b)

    await test_client.put(
        "/api/display-prefs/issue",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"display": SAMPLE_DISPLAY},
    )
    b_get = await test_client.get(
        "/api/display-prefs/issue",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert b_get.status_code == 200, b_get.text
    assert b_get.json()["data"]["display"] is None


@pytest.mark.asyncio
async def test_prefs_require_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "dp_hdr")
    resp = await test_client.get(
        "/api/display-prefs/issue",
        headers=_auth(user["token"]),
    )
    assert resp.status_code in (400, 403, 422)


@pytest.mark.asyncio
async def test_prefs_do_not_overwrite_saved_view_display(test_client: AsyncClient):
    user = await _register(test_client, "dp_sv")
    view_display = {"view_mode": "list", "group_by": "status"}
    created = await test_client.post(
        "/api/saved-views",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": "By status",
            "filter": {"tab": "open"},
            "display": view_display,
        },
    )
    assert created.status_code == 200, created.text
    view_id = created.json()["data"]["id"]

    put = await test_client.put(
        "/api/display-prefs/issue",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"display": SAMPLE_DISPLAY},
    )
    assert put.status_code == 200, put.text

    one = await test_client.get(
        f"/api/saved-views/{view_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.status_code == 200, one.text
    display = one.json()["data"]["display"]
    assert display["view_mode"] == "list"
    assert display["group_by"] == "status"
    assert display.get("swimlane_by") in (None, "none") or "swimlane_by" not in display or display.get(
        "swimlane_by"
    ) != "assignee"
