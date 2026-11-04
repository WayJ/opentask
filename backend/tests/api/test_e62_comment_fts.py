"""E62: Comment FTS mid — IssueComment → SearchBackend comments group."""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest import mock

import pytest
from httpx import AsyncClient
from sqlalchemy import select


async def _register(client: AsyncClient, prefix: str = "e62"):
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
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _project_and_issue(client: AsyncClient, h: dict, user_id: str, *, title: str = "Plain"):
    proj = await client.post(
        "/api/projects",
        headers=h,
        json={"name": f"P {uuid.uuid4().hex[:6]}", "description": "d"},
    )
    assert proj.status_code == 200, proj.text
    project_id = proj.json()["data"]["id"]
    issue = await client.post(
        "/api/issues",
        headers=h,
        json={
            "title": title,
            "description": "no needle here",
            "type": "bug",
            "status": "open",
            "priority": "medium",
            "reporter_id": user_id,
            "project_id": project_id,
        },
    )
    assert issue.status_code == 200, issue.text
    body = issue.json()["data"]
    return project_id, body["id"], body["issue_code"]


@pytest.mark.asyncio
async def test_e62_search_hits_comment_body(test_client: AsyncClient):
    user = await _register(test_client, "e62_hit")
    h = _auth(user["token"], user["workspaceId"])
    needle = f"cmtNeedle{uuid.uuid4().hex[:8]}"
    _, issue_id, issue_code = await _project_and_issue(
        test_client, h, user["userId"], title="Generic title without needle"
    )

    cmt = await test_client.post(
        f"/api/issues/{issue_id}/comments",
        headers=h,
        json={"content": f"Discussion mentions {needle} clearly"},
    )
    assert cmt.status_code == 200, cmt.text
    comment_id = cmt.json()["data"]["id"]

    resp = await test_client.get("/api/search", headers=h, params={"q": needle})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "comments" in data, data.keys()
    comments = data["comments"]
    assert any(c["id"] == comment_id for c in comments), comments
    hit = next(c for c in comments if c["id"] == comment_id)
    assert hit["issueId"] == issue_id
    assert hit["issueCode"] == issue_code
    assert hit.get("snippet") is None or len(hit["snippet"]) <= 120
    # title-only issue should not be forced into issues solely by comment needle
    assert not any(i["id"] == issue_id for i in data.get("issues") or [])


@pytest.mark.asyncio
async def test_e62_soft_deleted_issue_comments_hidden(test_client: AsyncClient):
    user = await _register(test_client, "e62_del")
    h = _auth(user["token"], user["workspaceId"])
    needle = f"delNeedle{uuid.uuid4().hex[:8]}"
    _, issue_id, _ = await _project_and_issue(test_client, h, user["userId"])

    cmt = await test_client.post(
        f"/api/issues/{issue_id}/comments",
        headers=h,
        json={"content": f"About to vanish {needle}"},
    )
    assert cmt.status_code == 200, cmt.text

    deleted = await test_client.delete(f"/api/issues/{issue_id}", headers=h)
    assert deleted.status_code == 200, deleted.text

    resp = await test_client.get("/api/search", headers=h, params={"q": needle})
    assert resp.status_code == 200, resp.text
    comments = resp.json()["data"].get("comments") or []
    assert comments == []


@pytest.mark.asyncio
async def test_e62_system_comment_type_excluded(test_client: AsyncClient, test_session):
    from opentask.models.issue.enums import CommentType
    from opentask.models.issue.model import IssueComment

    user = await _register(test_client, "e62_sys")
    h = _auth(user["token"], user["workspaceId"])
    needle = f"sysNeedle{uuid.uuid4().hex[:8]}"
    _, issue_id, _ = await _project_and_issue(test_client, h, user["userId"])

    # normal COMMENT via API
    cmt = await test_client.post(
        f"/api/issues/{issue_id}/comments",
        headers=h,
        json={"content": f"Human says {needle}"},
    )
    assert cmt.status_code == 200, cmt.text
    comment_id = cmt.json()["data"]["id"]

    # SYSTEM row inserted directly
    system = IssueComment(
        id=str(uuid.uuid4()),
        issue_id=issue_id,
        user_id=user["userId"],
        content=f"System also says {needle}",
        comment_type=CommentType.SYSTEM,
        is_deleted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_session.add(system)
    await test_session.commit()

    resp = await test_client.get("/api/search", headers=h, params={"q": needle})
    assert resp.status_code == 200, resp.text
    comments = resp.json()["data"]["comments"]
    ids = {c["id"] for c in comments}
    assert comment_id in ids
    assert system.id not in ids


@pytest.mark.asyncio
async def test_e62_nested_reply_is_own_hit(test_client: AsyncClient):
    user = await _register(test_client, "e62_nest")
    h = _auth(user["token"], user["workspaceId"])
    needle = f"nestNeedle{uuid.uuid4().hex[:8]}"
    _, issue_id, _ = await _project_and_issue(test_client, h, user["userId"])

    parent = await test_client.post(
        f"/api/issues/{issue_id}/comments",
        headers=h,
        json={"content": f"Parent has {needle}"},
    )
    assert parent.status_code == 200, parent.text
    parent_id = parent.json()["data"]["id"]

    reply = await test_client.post(
        f"/api/issues/{issue_id}/comments",
        headers=h,
        json={"content": f"Reply also has {needle}", "parent_id": parent_id},
    )
    assert reply.status_code == 200, reply.text
    reply_id = reply.json()["data"]["id"]

    resp = await test_client.get("/api/search", headers=h, params={"q": needle})
    assert resp.status_code == 200, resp.text
    ids = {c["id"] for c in resp.json()["data"]["comments"]}
    assert parent_id in ids and reply_id in ids


@pytest.mark.asyncio
async def test_e62_empty_q_includes_comments_key(test_client: AsyncClient):
    user = await _register(test_client, "e62_empty")
    resp = await test_client.get(
        "/api/search",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"q": "  "},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data == {
        "issues": [],
        "projects": [],
        "docs": [],
        "members": [],
        "comments": [],
    }


@pytest.mark.asyncio
async def test_e62_cross_tenant_forbidden(test_client: AsyncClient):
    a = await _register(test_client, "e62_a")
    b = await _register(test_client, "e62_b")
    resp = await test_client.get(
        "/api/search",
        headers=_auth(b["token"], a["workspaceId"]),
        params={"q": "anything"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_e62_e60_groups_still_present(test_client: AsyncClient):
    user = await _register(test_client, "e62_grp")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.get("/api/search", headers=h, params={"q": "zzzznone"})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    for key in ("issues", "projects", "docs", "members", "comments"):
        assert key in data
        assert data[key] == []


@pytest.mark.asyncio
async def test_e62_no_emit_fire_webhooks(test_client: AsyncClient):
    user = await _register(test_client, "e62_ne")
    h = _auth(user["token"], user["workspaceId"])
    with mock.patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=mock.AsyncMock,
    ) as fire_spy:
        resp = await test_client.get("/api/search", headers=h, params={"q": "noop"})
        assert resp.status_code == 200, resp.text
        fire_spy.assert_not_called()
