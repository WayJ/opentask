"""E3-S3：Inbox 通知流（指派 / 评论 / @mention）"""
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ib"):
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
async def test_assign_creates_notification(test_client: AsyncClient):
    owner = await _register(test_client, "asg_o")
    member = await _register(test_client, "asg_m")
    await _add_member(test_client, owner, member)

    issue = await _create_issue(test_client, owner, "assign-me")

    resp = await test_client.put(
        f"/api/issues/{issue['id']}/assignee",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"assignee_id": member["userId"]},
    )
    assert resp.status_code == 200, resp.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert inbox.status_code == 200, inbox.text
    data = inbox.json()["data"]
    assert data["total"] >= 1
    types = {r["type"] for r in data["rows"]}
    assert "assigned" in types
    assert any(r["resourceId"] == issue["id"] and r["type"] == "assigned" for r in data["rows"])
    # 指派者自己不应收到
    own = await test_client.get(
        "/api/inbox",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert own.status_code == 200
    own_assigned = [
        r
        for r in own.json()["data"]["rows"]
        if r["resourceId"] == issue["id"] and r["type"] == "assigned"
    ]
    assert own_assigned == []


@pytest.mark.asyncio
async def test_comment_notifies_assignee_not_author(test_client: AsyncClient):
    owner = await _register(test_client, "cmt_o")
    member = await _register(test_client, "cmt_m")
    await _add_member(test_client, owner, member)

    issue = await _create_issue(
        test_client, owner, "comment-target", assignee_id=member["userId"]
    )
    # 指派会先产生 assigned；清一下未读视角——后续只断言 commented
    await test_client.post(
        "/api/inbox/read-all",
        headers=_auth(member["token"], owner["workspaceId"]),
    )

    resp = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"content": "please take a look"},
    )
    assert resp.status_code == 200, resp.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"unread_only": True},
    )
    assert inbox.status_code == 200, inbox.text
    rows = inbox.json()["data"]["rows"]
    commented = [r for r in rows if r["type"] == "commented" and r["resourceId"] == issue["id"]]
    assert len(commented) >= 1

    # 作者无自通知
    author_inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"unread_only": True},
    )
    author_rows = author_inbox.json()["data"]["rows"]
    assert not any(
        r["resourceId"] == issue["id"] and r["type"] == "commented" for r in author_rows
    )


@pytest.mark.asyncio
async def test_mention_notifies_workspace_member(test_client: AsyncClient):
    owner = await _register(test_client, "men_o")
    member = await _register(test_client, "men_m")
    await _add_member(test_client, owner, member)

    issue = await _create_issue(test_client, owner, "mention-me")
    await test_client.post(
        "/api/inbox/read-all",
        headers=_auth(member["token"], owner["workspaceId"]),
    )

    content = f"hey @{member['username']} check this"
    resp = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"content": content},
    )
    assert resp.status_code == 200, resp.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"unread_only": True},
    )
    assert inbox.status_code == 200, inbox.text
    rows = inbox.json()["data"]["rows"]
    mentioned = [r for r in rows if r["type"] == "mentioned" and r["resourceId"] == issue["id"]]
    assert len(mentioned) >= 1


@pytest.mark.asyncio
async def test_inbox_list_isolation(test_client: AsyncClient):
    a = await _register(test_client, "iso_a")
    b = await _register(test_client, "iso_b")
    await _add_member(test_client, a, b)

    issue = await _create_issue(test_client, a, "iso-issue")
    await test_client.put(
        f"/api/issues/{issue['id']}/assignee",
        headers=_auth(a["token"], a["workspaceId"]),
        params={"assignee_id": b["userId"]},
    )

    a_inbox = await test_client.get(
        "/api/inbox", headers=_auth(a["token"], a["workspaceId"])
    )
    b_inbox = await test_client.get(
        "/api/inbox", headers=_auth(b["token"], a["workspaceId"])
    )
    assert a_inbox.status_code == 200 and b_inbox.status_code == 200
    a_ids = {r["id"] for r in a_inbox.json()["data"]["rows"]}
    b_ids = {r["id"] for r in b_inbox.json()["data"]["rows"]}
    # B 应有 assigned；A 不应看到 B 的通知 id
    assert b_ids
    assert a_ids.isdisjoint(b_ids)


@pytest.mark.asyncio
async def test_mark_read_and_unread_filter(test_client: AsyncClient):
    owner = await _register(test_client, "rd_o")
    member = await _register(test_client, "rd_m")
    await _add_member(test_client, owner, member)

    issue = await _create_issue(test_client, owner, "read-me")
    await test_client.put(
        f"/api/issues/{issue['id']}/assignee",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"assignee_id": member["userId"]},
    )

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"unread_only": True},
    )
    rows = inbox.json()["data"]["rows"]
    assert rows
    nid = rows[0]["id"]

    mark = await test_client.post(
        f"/api/inbox/{nid}/read",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert mark.status_code == 200, mark.text
    assert mark.json()["data"]["readAt"] is not None

    unread = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"unread_only": True},
    )
    unread_ids = {r["id"] for r in unread.json()["data"]["rows"]}
    assert nid not in unread_ids

    # read-all 也不应报错
    all_mark = await test_client.post(
        "/api/inbox/read-all",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert all_mark.status_code == 200, all_mark.text
