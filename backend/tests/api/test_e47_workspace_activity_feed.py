"""E47：WS Activity Feed v1 — JSON cursor API + no-emit."""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Unit: cursor + clamp
# ---------------------------------------------------------------------------


def test_activity_cursor_roundtrip():
    from opentask.services.issue_timeline_export import (
        decode_activity_cursor,
        encode_activity_cursor,
    )

    ts = datetime(2026, 11, 5, 1, 2, 3, 456789)
    rid = "abc-def-012"
    cur = encode_activity_cursor(ts, rid)
    assert isinstance(cur, str) and len(cur) > 8
    got_ts, got_id = decode_activity_cursor(cur)
    assert got_ts == ts
    assert got_id == rid


def test_activity_cursor_invalid_raises():
    from opentask.services.issue_timeline_export import decode_activity_cursor

    with pytest.raises(ValueError):
        decode_activity_cursor("not-a-cursor!!!")
    with pytest.raises(ValueError):
        decode_activity_cursor(base64.urlsafe_b64encode(b"only-one-part").decode())


def test_clamp_activity_limit():
    from opentask.services.issue_timeline_export import clamp_activity_limit

    assert clamp_activity_limit(50) == 50
    assert clamp_activity_limit(500) == 200
    assert clamp_activity_limit(200) == 200
    assert clamp_activity_limit(0) == 1
    assert clamp_activity_limit(-5) == 1


# ---------------------------------------------------------------------------
# Helpers (mirror E41)
# ---------------------------------------------------------------------------


async def _register(client: AsyncClient, prefix: str = "e47"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _create_issue(client: AsyncClient, user: dict, title: str = "e47-issue", **extra) -> dict:
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


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_empty_workspace(test_client: AsyncClient):
    user = await _register(test_client)
    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["items"] == []
    assert body["nextCursor"] is None


@pytest.mark.asyncio
async def test_activity_lists_status_change_with_issue_meta(test_client: AsyncClient):
    user = await _register(test_client)
    issue = await _create_issue(test_client, user, title="feed-me")
    upd = await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "in_progress"},
    )
    assert upd.status_code == 200, upd.text

    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"actionType": "status_changed"},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    row = items[0]
    assert row["actionType"] == "status_changed"
    assert row["issueId"] == issue["id"]
    assert row["issueCode"]
    assert row["issueTitle"] == "feed-me"
    assert row["actor"]["id"] == user["userId"]
    assert "createdAt" in row
    assert isinstance(row["payload"], dict)


@pytest.mark.asyncio
async def test_activity_filters_and_cursor_and_clamp(test_client: AsyncClient):
    user = await _register(test_client)
    a = await _create_issue(test_client, user, title="A")
    b = await _create_issue(test_client, user, title="B")
    for issue in (a, b):
        r = await test_client.put(
            f"/api/issues/{issue['id']}/status",
            headers=_auth(user["token"], user["workspaceId"]),
            params={"status": "in_progress"},
        )
        assert r.status_code == 200, r.text
        r2 = await test_client.put(
            f"/api/issues/{issue['id']}/priority",
            headers=_auth(user["token"], user["workspaceId"]),
            params={"priority": "high"},
        )
        assert r2.status_code == 200, r2.text

    # issue filter
    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"issueId": a["id"]},
    )
    assert resp.status_code == 200, resp.text
    for it in resp.json()["data"]["items"]:
        assert it["issueId"] == a["id"]

    # actor filter
    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"actorId": user["userId"], "limit": 2},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert len(data["items"]) == 2
    assert data["nextCursor"]
    page1_ids = [i["id"] for i in data["items"]]

    resp2 = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"actorId": user["userId"], "limit": 2, "cursor": data["nextCursor"]},
    )
    assert resp2.status_code == 200, resp2.text
    page2_ids = [i["id"] for i in resp2.json()["data"]["items"]]
    assert set(page1_ids).isdisjoint(set(page2_ids))

    # clamp
    resp3 = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"limit": 500},
    )
    assert resp3.status_code == 200, resp3.text
    assert len(resp3.json()["data"]["items"]) <= 200


@pytest.mark.asyncio
async def test_activity_invalid_action_type_and_cursor(test_client: AsyncClient):
    user = await _register(test_client)
    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"actionType": "not_a_real_action"},
    )
    assert resp.status_code == 400

    resp2 = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"cursor": "%%%bad%%%"},
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_activity_cross_tenant_isolated(test_client: AsyncClient):
    u1 = await _register(test_client, "e47a")
    u2 = await _register(test_client, "e47b")
    issue = await _create_issue(test_client, u1, title="secret")
    await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(u1["token"], u1["workspaceId"]),
        params={"status": "closed"},
    )
    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(u2["token"], u2["workspaceId"]),
        params={"issueId": issue["id"]},
    )
    # 404 for foreign issueId OR empty — either is ok; must not leak rows
    if resp.status_code == 200:
        assert resp.json()["data"]["items"] == []
    else:
        assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_activity_read_path_no_emit(test_client: AsyncClient):
    user = await _register(test_client)
    issue = await _create_issue(test_client, user)
    await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "in_progress"},
    )
    with (
        patch(
            "opentask.services.workspace_webhook.service.fire_webhooks",
            new_callable=AsyncMock,
        ) as wh,
        patch(
            "opentask.services.automation.service.fire_automations",
            new_callable=AsyncMock,
        ) as auto,
    ):
        resp = await test_client.get(
            "/api/issues/activity",
            headers=_auth(user["token"], user["workspaceId"]),
        )
        assert resp.status_code == 200, resp.text
        wh.assert_not_called()
        auto.assert_not_called()
