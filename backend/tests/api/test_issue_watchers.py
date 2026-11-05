"""E18：Issue watch / unwatch + Inbox fanout + tenant checks"""
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "iw"):
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
async def test_watch_unwatch_idempotent(test_client: AsyncClient):
    owner = await _register(test_client, "iw_wo")
    member = await _register(test_client, "iw_wm")
    await _add_member(test_client, owner, member)
    issue = await _create_issue(test_client, owner, "Watch me")

    listed = await test_client.get(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    assert all(r["user_id"] != member["userId"] for r in listed.json()["data"])

    w1 = await test_client.post(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w1.status_code == 200, w1.text
    w2 = await test_client.post(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w2.status_code == 200, w2.text

    listed2 = await test_client.get(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    ids = [r["user_id"] for r in listed2.json()["data"]]
    assert ids.count(member["userId"]) == 1

    deleted = await test_client.delete(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text
    listed3 = await test_client.get(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert all(r["user_id"] != member["userId"] for r in listed3.json()["data"])


@pytest.mark.asyncio
async def test_watch_cross_tenant_forbidden(test_client: AsyncClient):
    a = await _register(test_client, "iw_ta")
    b = await _register(test_client, "iw_tb")
    issue = await _create_issue(test_client, a, "Secret")

    # wrong workspace header (b's WS) against a's issue → 403/404
    resp = await test_client.post(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert resp.status_code in (403, 404), resp.text

    listed = await test_client.get(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert listed.status_code in (403, 404), listed.text


@pytest.mark.asyncio
async def test_comment_fanout_to_watcher(test_client: AsyncClient):
    owner = await _register(test_client, "iw_co")
    member = await _register(test_client, "iw_cm")
    await _add_member(test_client, owner, member)
    issue = await _create_issue(test_client, owner, "Commented watch")

    watch = await test_client.post(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert watch.status_code == 200, watch.text

    comment = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"content": "hello watcher"},
    )
    assert comment.status_code == 200, comment.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"page": 1, "page_size": 20},
    )
    assert inbox.status_code == 200, inbox.text
    rows = inbox.json()["data"]["rows"]
    assert any(
        r["type"] == "commented" and r["resourceId"] == issue["id"] for r in rows
    ), rows

    # actor (owner) should not get self-notify from own comment as watcher
    # (owner wasn't watching; even if watching, actor skipped)


@pytest.mark.asyncio
async def test_status_and_assignee_fanout_to_watcher(test_client: AsyncClient):
    owner = await _register(test_client, "iw_so")
    member = await _register(test_client, "iw_sm")
    other = await _register(test_client, "iw_ot")
    await _add_member(test_client, owner, member)
    await _add_member(test_client, owner, other)
    issue = await _create_issue(test_client, owner, "Status watch")

    watch = await test_client.post(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert watch.status_code == 200, watch.text

    upd = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    assert upd.status_code == 200, upd.text

    assign = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"assignee_id": other["userId"]},
    )
    assert assign.status_code == 200, assign.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"page": 1, "page_size": 50},
    )
    assert inbox.status_code == 200, inbox.text
    rows = inbox.json()["data"]["rows"]
    types = {r["type"] for r in rows if r["resourceId"] == issue["id"]}
    assert "status_changed" in types, rows
    assert "subscribed_update" in types, rows

    # new assignee gets assigned; watcher got subscribed_update (not duplicate assigned)
    other_inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(other["token"], owner["workspaceId"]),
        params={"page": 1, "page_size": 50},
    )
    assert other_inbox.status_code == 200, other_inbox.text
    other_rows = other_inbox.json()["data"]["rows"]
    assert any(
        r["type"] == "assigned" and r["resourceId"] == issue["id"] for r in other_rows
    ), other_rows
