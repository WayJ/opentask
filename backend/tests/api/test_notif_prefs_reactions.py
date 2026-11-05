"""E27：通知偏好 + 评论 Reactions."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "np"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "np-issue", **extra) -> dict:
    payload = {
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
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_prefs_default_and_put(test_client: AsyncClient):
    user = await _register(test_client, "np_def")
    h = _auth(user["token"], user["workspaceId"])

    got = await test_client.get("/api/inbox/preferences", headers=h)
    assert got.status_code == 200, got.text
    data = got.json()["data"]
    assert data["issue_comment"] is True
    assert data["issue_assigned"] is True
    assert data["userId"] == user["userId"]
    assert data["workspaceId"] == user["workspaceId"]

    put = await test_client.put(
        "/api/inbox/preferences",
        headers=h,
        json={"issue_comment": False, "issue_mention": False},
    )
    assert put.status_code == 200, put.text
    pdata = put.json()["data"]
    assert pdata["issue_comment"] is False
    assert pdata["issue_mention"] is False
    assert pdata["issue_assigned"] is True  # untouched

    got2 = await test_client.get("/api/inbox/preferences", headers=h)
    assert got2.json()["data"]["issue_comment"] is False


@pytest.mark.asyncio
async def test_prefs_require_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "np_hdr")
    resp = await test_client.get(
        "/api/inbox/preferences",
        headers={"Authorization": f"Bearer {user['token']}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_disable_issue_comment_skips_inbox(test_client: AsyncClient):
    owner = await _register(test_client, "np_o")
    member = await _register(test_client, "np_m")
    await _add_member(test_client, owner, member)

    issue = await _create_issue(
        test_client, owner, "comment-pref", assignee_id=member["userId"]
    )

    # member turns off issue_comment
    await test_client.put(
        "/api/inbox/preferences",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"issue_comment": False},
    )

    # owner comments
    resp = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"content": "hello assignee"},
    )
    assert resp.status_code == 200, resp.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert inbox.status_code == 200
    commented = [
        r
        for r in inbox.json()["data"]["rows"]
        if r["resourceId"] == issue["id"] and r["type"] == "commented"
    ]
    assert commented == []


@pytest.mark.asyncio
async def test_prefs_isolated_across_users(test_client: AsyncClient):
    owner = await _register(test_client, "np_iso_o")
    m1 = await _register(test_client, "np_iso_a")
    m2 = await _register(test_client, "np_iso_b")
    await _add_member(test_client, owner, m1)
    await _add_member(test_client, owner, m2)

    issue = await _create_issue(
        test_client, owner, "iso-comment", assignee_id=m1["userId"]
    )
    # also set reporter somehow — create with reporter owner; assign m1.
    # Add m2 as watcher via API if available, or just mention both.
    # Simpler: assign m1, comment notifies assignee m1; reporter is owner (skipped as actor).
    # For m2: mention @username

    await test_client.put(
        "/api/inbox/preferences",
        headers=_auth(m1["token"], owner["workspaceId"]),
        json={"issue_comment": False},
    )
    # m2 keeps defaults

    resp = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"content": f"hi @{m2['username']} and team"},
    )
    assert resp.status_code == 200, resp.text

    inbox_m1 = await test_client.get(
        "/api/inbox", headers=_auth(m1["token"], owner["workspaceId"])
    )
    m1_commented = [
        r
        for r in inbox_m1.json()["data"]["rows"]
        if r["resourceId"] == issue["id"] and r["type"] == "commented"
    ]
    assert m1_commented == []

    inbox_m2 = await test_client.get(
        "/api/inbox", headers=_auth(m2["token"], owner["workspaceId"])
    )
    m2_mentioned = [
        r
        for r in inbox_m2.json()["data"]["rows"]
        if r["resourceId"] == issue["id"] and r["type"] == "mentioned"
    ]
    assert len(m2_mentioned) >= 1


@pytest.mark.asyncio
async def test_cross_tenant_prefs_forbidden(test_client: AsyncClient):
    a = await _register(test_client, "np_xa")
    b = await _register(test_client, "np_xb")
    resp = await test_client.get(
        "/api/inbox/preferences",
        headers=_auth(a["token"], b["workspaceId"]),
    )
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_comment_reactions_crud(test_client: AsyncClient):
    user = await _register(test_client, "cr_u")
    issue = await _create_issue(test_client, user, "rx-issue")
    h = _auth(user["token"], user["workspaceId"])

    c = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=h,
        json={"content": "react to me"},
    )
    assert c.status_code == 200, c.text
    cid = c.json()["data"]["id"]

    add = await test_client.post(
        f"/api/issues/{issue['id']}/comments/{cid}/reactions",
        headers=h,
        json={"emoji": "👍"},
    )
    assert add.status_code == 200, add.text
    assert "👍" in add.json()["data"]["reactions"]
    assert user["userId"] in add.json()["data"]["reactions"]["👍"]

    got = await test_client.get(
        f"/api/issues/{issue['id']}/comments/{cid}/reactions",
        headers=h,
    )
    assert got.status_code == 200
    assert user["userId"] in got.json()["data"]["reactions"]["👍"]

    # list comments includes reactions
    listing = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    assert listing.status_code == 200
    rows = listing.json()["data"]["rows"]
    target = next(r for r in rows if r["id"] == cid)
    assert user["userId"] in target["reactions"]["👍"]

    rm = await test_client.delete(
        f"/api/issues/{issue['id']}/comments/{cid}/reactions",
        headers=h,
        params={"emoji": "👍"},
    )
    assert rm.status_code == 200, rm.text
    assert user["userId"] not in (rm.json()["data"]["reactions"].get("👍") or [])


@pytest.mark.asyncio
async def test_comment_reactions_cross_tenant(test_client: AsyncClient):
    a = await _register(test_client, "cr_xa")
    b = await _register(test_client, "cr_xb")
    issue = await _create_issue(test_client, a, "rx-x")
    c = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"content": "private"},
    )
    cid = c.json()["data"]["id"]

    resp = await test_client.post(
        f"/api/issues/{issue['id']}/comments/{cid}/reactions",
        headers=_auth(b["token"], b["workspaceId"]),
        json={"emoji": "🎉"},
    )
    assert resp.status_code in (403, 404)
