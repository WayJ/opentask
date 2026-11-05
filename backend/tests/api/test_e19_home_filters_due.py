"""E19：Home/My Issues 滤参 · due_date → Inbox · watchers 展示字段"""
import uuid
from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e19"):
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
async def test_list_assignee_me_and_reporter_me(test_client: AsyncClient):
    owner = await _register(test_client, "e19_me")
    member = await _register(test_client, "e19_mm")
    await _add_member(test_client, owner, member)

    mine = await _create_issue(
        test_client, owner, "Assigned to owner", assignee_id=owner["userId"]
    )
    theirs = await _create_issue(
        test_client, owner, "Assigned to member", assignee_id=member["userId"]
    )
    created_by_member = await _create_issue(
        test_client,
        {**member, "workspaceId": owner["workspaceId"]},
        "Created by member",
        reporter_id=member["userId"],
    )

    # assignee=me as owner
    resp = await test_client.get(
        "/api/issues",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"assignee_id": "me", "page_size": 50},
    )
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()["data"]["rows"]}
    assert mine["id"] in ids
    assert theirs["id"] not in ids

    # reporter=me as member in owner's WS
    resp2 = await test_client.get(
        "/api/issues",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"reporter_id": "me", "page_size": 50},
    )
    assert resp2.status_code == 200, resp2.text
    ids2 = {r["id"] for r in resp2.json()["data"]["rows"]}
    assert created_by_member["id"] in ids2
    assert mine["id"] not in ids2


@pytest.mark.asyncio
async def test_list_watching_filter(test_client: AsyncClient):
    owner = await _register(test_client, "e19_wo")
    member = await _register(test_client, "e19_wm")
    await _add_member(test_client, owner, member)
    watched = await _create_issue(test_client, owner, "Watched issue")
    other = await _create_issue(test_client, owner, "Not watched")

    w = await test_client.post(
        f"/api/issues/{watched['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w.status_code == 200, w.text

    resp = await test_client.get(
        "/api/issues",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"watching": "true", "page_size": 50},
    )
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()["data"]["rows"]}
    assert watched["id"] in ids
    assert other["id"] not in ids


@pytest.mark.asyncio
async def test_list_due_soon_and_due_before(test_client: AsyncClient):
    owner = await _register(test_client, "e19_due")
    today = date.today()
    soon = await _create_issue(
        test_client,
        owner,
        "Due in 2 days",
        due_date=(datetime.combine(today + timedelta(days=2), datetime.min.time())).isoformat(),
    )
    far = await _create_issue(
        test_client,
        owner,
        "Due in 10 days",
        due_date=(datetime.combine(today + timedelta(days=10), datetime.min.time())).isoformat(),
    )
    closed_soon = await _create_issue(
        test_client,
        owner,
        "Closed but due soon",
        due_date=(datetime.combine(today + timedelta(days=1), datetime.min.time())).isoformat(),
        status="closed",
    )

    resp = await test_client.get(
        "/api/issues",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"due_soon": "true", "page_size": 50},
    )
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()["data"]["rows"]}
    assert soon["id"] in ids
    assert far["id"] not in ids
    assert closed_soon["id"] not in ids

    before = (today + timedelta(days=3)).isoformat()
    resp2 = await test_client.get(
        "/api/issues",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"due_before": before, "page_size": 50},
    )
    assert resp2.status_code == 200, resp2.text
    ids2 = {r["id"] for r in resp2.json()["data"]["rows"]}
    assert soon["id"] in ids2
    assert far["id"] not in ids2


@pytest.mark.asyncio
async def test_due_date_change_notifies_assignee_and_watchers(test_client: AsyncClient):
    owner = await _register(test_client, "e19_dn")
    assignee = await _register(test_client, "e19_as")
    watcher = await _register(test_client, "e19_wa")
    await _add_member(test_client, owner, assignee)
    await _add_member(test_client, owner, watcher)

    issue = await _create_issue(
        test_client, owner, "Due notify", assignee_id=assignee["userId"]
    )
    watch = await test_client.post(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(watcher["token"], owner["workspaceId"]),
    )
    assert watch.status_code == 200, watch.text

    new_due = (datetime.utcnow() + timedelta(days=5)).isoformat()
    upd = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"due_date": new_due},
    )
    assert upd.status_code == 200, upd.text

    # timeline
    tl = await test_client.get(
        f"/api/issues/{issue['id']}/timeline",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert tl.status_code == 200, tl.text
    actions = [r.get("action_type") or r.get("actionType") for r in tl.json()["data"]["rows"]]
    assert "due_date_changed" in actions, actions

    for user in (assignee, watcher):
        inbox = await test_client.get(
            "/api/inbox",
            headers=_auth(user["token"], owner["workspaceId"]),
            params={"page": 1, "page_size": 50},
        )
        assert inbox.status_code == 200, inbox.text
        rows = inbox.json()["data"]["rows"]
        assert any(
            r["type"] == "due_date_changed" and r["resourceId"] == issue["id"] for r in rows
        ), (user["username"], rows)

    # actor (owner) should not receive
    owner_inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"page": 1, "page_size": 50},
    )
    assert owner_inbox.status_code == 200
    owner_rows = owner_inbox.json()["data"]["rows"]
    assert not any(
        r["type"] == "due_date_changed" and r["resourceId"] == issue["id"] for r in owner_rows
    ), owner_rows


@pytest.mark.asyncio
async def test_watchers_list_includes_username(test_client: AsyncClient):
    owner = await _register(test_client, "e19_wu")
    member = await _register(test_client, "e19_wn")
    await _add_member(test_client, owner, member)
    issue = await _create_issue(test_client, owner, "Watcher names")
    await test_client.post(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    listed = await test_client.get(
        f"/api/issues/{issue['id']}/watchers",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]
    hit = next(r for r in rows if r["user_id"] == member["userId"])
    assert hit.get("username") == member["username"] or hit.get("name")
