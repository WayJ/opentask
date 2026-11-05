"""E74: comment threading mid — depth=1 replies, soft-delete hide, notify parent author."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e74"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h


async def _add_member(client: AsyncClient, owner: dict, member: dict):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": "member"},
    )
    assert resp.status_code == 200, resp.text


async def _issue(client: AsyncClient, user: dict, title: str = "E74") -> dict:
    r = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": title,
            "type": "bug",
            "reporter_id": user["userId"],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def _comment(
    client: AsyncClient,
    user: dict,
    issue_id: str,
    content: str = "hi",
    parent_id: str | None = None,
):
    body: dict = {"content": content}
    if parent_id is not None:
        body["parent_id"] = parent_id
    r = await client.post(
        f"/api/issues/{issue_id}/comments",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    return r


@pytest.mark.asyncio
async def test_e74_reply_to_root_ok(test_client: AsyncClient):
    user = await _register(test_client, "e74_ok")
    issue = await _issue(test_client, user)
    root = await _comment(test_client, user, issue["id"], "root")
    assert root.status_code == 200, root.text
    root_id = root.json()["data"]["id"]

    reply = await _comment(test_client, user, issue["id"], "reply", parent_id=root_id)
    assert reply.status_code == 200, reply.text
    data = reply.json()["data"]
    assert data["parent_id"] == root_id

    listed = await test_client.get(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert len(rows) == 2
    by_id = {r["id"]: r for r in rows}
    assert by_id[root_id]["parent_id"] in (None, "")
    assert by_id[data["id"]]["parent_id"] == root_id


@pytest.mark.asyncio
async def test_e74_parent_cross_issue_400(test_client: AsyncClient):
    user = await _register(test_client, "e74_x")
    i1 = await _issue(test_client, user, "A")
    i2 = await _issue(test_client, user, "B")
    root = await _comment(test_client, user, i1["id"], "on-a")
    assert root.status_code == 200
    root_id = root.json()["data"]["id"]

    bad = await _comment(test_client, user, i2["id"], "cross", parent_id=root_id)
    assert bad.status_code == 400, bad.text
    detail = bad.json().get("detail") or bad.json()
    code = detail.get("code") if isinstance(detail, dict) else None
    if code is None and isinstance(detail, dict) and "detail" in detail:
        code = detail["detail"].get("code") if isinstance(detail["detail"], dict) else None
    # FastAPI may wrap detail
    blob = bad.text
    assert "parent_cross_issue" in blob or code == "parent_cross_issue"


@pytest.mark.asyncio
async def test_e74_parent_not_found_400(test_client: AsyncClient):
    user = await _register(test_client, "e74_nf")
    issue = await _issue(test_client, user)
    bad = await _comment(
        test_client, user, issue["id"], "x", parent_id=str(uuid.uuid4())
    )
    assert bad.status_code == 400, bad.text
    assert "parent_not_found" in bad.text


@pytest.mark.asyncio
async def test_e74_reply_to_reply_400(test_client: AsyncClient):
    user = await _register(test_client, "e74_d2")
    issue = await _issue(test_client, user)
    root = await _comment(test_client, user, issue["id"], "root")
    root_id = root.json()["data"]["id"]
    reply = await _comment(test_client, user, issue["id"], "r1", parent_id=root_id)
    assert reply.status_code == 200, reply.text
    reply_id = reply.json()["data"]["id"]

    deep = await _comment(test_client, user, issue["id"], "r2", parent_id=reply_id)
    assert deep.status_code == 400, deep.text
    assert "parent_not_root" in deep.text


@pytest.mark.asyncio
async def test_e74_deleted_parent_400(test_client: AsyncClient):
    user = await _register(test_client, "e74_delp")
    issue = await _issue(test_client, user)
    root = await _comment(test_client, user, issue["id"], "root")
    root_id = root.json()["data"]["id"]
    deleted = await test_client.delete(
        f"/api/issues/comments/{root_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    bad = await _comment(test_client, user, issue["id"], "late", parent_id=root_id)
    assert bad.status_code == 400, bad.text
    assert "parent_deleted" in bad.text


@pytest.mark.asyncio
async def test_e74_soft_delete_parent_hides_children(test_client: AsyncClient):
    user = await _register(test_client, "e74_hide")
    issue = await _issue(test_client, user)
    root = await _comment(test_client, user, issue["id"], "root")
    root_id = root.json()["data"]["id"]
    reply = await _comment(test_client, user, issue["id"], "child", parent_id=root_id)
    assert reply.status_code == 200
    reply_id = reply.json()["data"]["id"]

    deleted = await test_client.delete(
        f"/api/issues/comments/{root_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    listed = await test_client.get(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200
    ids = {r["id"] for r in listed.json()["data"]["rows"]}
    assert root_id not in ids
    assert reply_id not in ids


@pytest.mark.asyncio
async def test_e74_reply_notifies_parent_author(test_client: AsyncClient):
    owner = await _register(test_client, "e74_no")
    member = await _register(test_client, "e74_nm")
    await _add_member(test_client, owner, member)

    # Issue owned/reported by owner; no assignee → member only gets notif via parent-author fanout
    issue = await _issue(test_client, owner, "thread-notif")
    root = await _comment(test_client, member, issue["id"], "i am parent author")
    assert root.status_code == 200, root.text
    root_id = root.json()["data"]["id"]

    await test_client.post(
        "/api/inbox/read-all",
        headers=_auth(member["token"], owner["workspaceId"]),
    )

    reply = await _comment(
        test_client, owner, issue["id"], "reply to you", parent_id=root_id
    )
    assert reply.status_code == 200, reply.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"unread_only": True},
    )
    assert inbox.status_code == 200, inbox.text
    rows = inbox.json()["data"]["rows"]
    commented = [
        r
        for r in rows
        if r["type"] == "commented" and r["resourceId"] == issue["id"]
    ]
    assert len(commented) >= 1


@pytest.mark.asyncio
async def test_e74_no_new_webhook_event_name(test_client: AsyncClient):
    user = await _register(test_client, "e74_wh")
    issue = await _issue(test_client, user)
    root = await _comment(test_client, user, issue["id"], "root")
    root_id = root.json()["data"]["id"]

    with patch(
        "opentask.services.issue_service.fire_webhooks", new_callable=AsyncMock
    ) as fw:
        reply = await _comment(
            test_client, user, issue["id"], "r", parent_id=root_id
        )
        assert reply.status_code == 200, reply.text
        assert fw.await_count >= 1
        event_types = set()
        for call in fw.call_args_list:
            et = call.kwargs.get("event_type")
            if et is None and len(call.args) >= 3:
                maybe = call.args[2]
                if isinstance(maybe, str):
                    et = maybe
            if et:
                event_types.add(et)
        assert "comment.created" in event_types
        assert "comment.replied" not in event_types
        assert "issue.comment_replied" not in event_types
