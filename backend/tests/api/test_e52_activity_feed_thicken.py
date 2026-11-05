"""E52：Activity Feed thicken — watching · reactions · unread bell · no-emit."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e52"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "e52-issue", **extra) -> dict:
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


async def _watch(client: AsyncClient, user: dict, issue_id: str, workspace_id: str | None = None):
    ws = workspace_id or user["workspaceId"]
    resp = await client.post(
        f"/api/issues/{issue_id}/watchers",
        headers=_auth(user["token"], ws),
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------


def test_build_reaction_summary_unit():
    from opentask.services.issue_timeline_export import build_reaction_summary

    summary = build_reaction_summary(
        {"👍": ["u1", "u2"], "🎉": ["u3"]},
        viewer_id="u1",
    )
    by_emoji = {s["emoji"]: s for s in summary}
    assert by_emoji["👍"]["count"] == 2
    assert by_emoji["👍"]["myReacted"] is True
    assert by_emoji["🎉"]["myReacted"] is False


def test_format_unread_cap_unit():
    from opentask.services.issue_timeline_export import clamp_unread_count

    assert clamp_unread_count(0) == (0, False)
    assert clamp_unread_count(5) == (5, False)
    assert clamp_unread_count(99) == (99, False)
    assert clamp_unread_count(100) == (99, True)
    assert clamp_unread_count(500) == (99, True)


# ---------------------------------------------------------------------------
# A: watching filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_watching_filters_to_watched_issues(test_client: AsyncClient):
    user = await _register(test_client, "e52w")
    a = await _create_issue(test_client, user, title="watched")
    b = await _create_issue(test_client, user, title="unwatched")
    await _watch(test_client, user, a["id"])
    for issue in (a, b):
        r = await test_client.put(
            f"/api/issues/{issue['id']}/status",
            headers=_auth(user["token"], user["workspaceId"]),
            params={"status": "in_progress"},
        )
        assert r.status_code == 200, r.text

    full = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"actionType": "status_changed"},
    )
    assert full.status_code == 200, full.text
    full_ids = {i["issueId"] for i in full.json()["data"]["items"]}
    assert a["id"] in full_ids and b["id"] in full_ids

    watched = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"watching": "true", "actionType": "status_changed"},
    )
    assert watched.status_code == 200, watched.text
    items = watched.json()["data"]["items"]
    assert items
    assert all(i["issueId"] == a["id"] for i in items)
    assert b["id"] not in {i["issueId"] for i in items}


@pytest.mark.asyncio
async def test_activity_watching_empty_when_no_watches(test_client: AsyncClient):
    user = await _register(test_client, "e52empty")
    issue = await _create_issue(test_client, user)
    await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "in_progress"},
    )
    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"watching": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_activity_watching_cross_tenant(test_client: AsyncClient):
    u1 = await _register(test_client, "e52t1")
    u2 = await _register(test_client, "e52t2")
    issue = await _create_issue(test_client, u1, title="secret-watch")
    await _watch(test_client, u1, issue["id"])
    await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(u1["token"], u1["workspaceId"]),
        params={"status": "closed"},
    )
    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(u2["token"], u2["workspaceId"]),
        params={"watching": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["items"] == []


# ---------------------------------------------------------------------------
# B: reactions summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_includes_issue_reaction_summary(test_client: AsyncClient):
    user = await _register(test_client, "e52rx")
    issue = await _create_issue(test_client, user)
    await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "in_progress"},
    )
    add = await test_client.post(
        f"/api/issues/{issue['id']}/reactions",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"emoji": "👍"},
    )
    assert add.status_code == 200, add.text

    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"actionType": "status_changed"},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]["items"]
    assert items
    row = items[0]
    assert "reactions" in row
    assert row["reactions"]["scope"] == "issue"
    summary = {s["emoji"]: s for s in row["reactions"]["summary"]}
    assert summary["👍"]["count"] >= 1
    assert summary["👍"]["myReacted"] is True


@pytest.mark.asyncio
async def test_activity_comment_row_uses_comment_reactions(test_client: AsyncClient):
    user = await _register(test_client, "e52cr")
    issue = await _create_issue(test_client, user)
    cmt = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"content": "hello e52"},
    )
    assert cmt.status_code == 200, cmt.text
    cid = cmt.json()["data"]["id"]
    add = await test_client.post(
        f"/api/issues/{issue['id']}/comments/{cid}/reactions",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"emoji": "🎉"},
    )
    assert add.status_code == 200, add.text

    resp = await test_client.get(
        "/api/issues/activity",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"actionType": "commented"},
    )
    assert resp.status_code == 200, resp.text
    items = [i for i in resp.json()["data"]["items"] if i["actionType"] == "commented"]
    assert items
    row = items[0]
    assert row["reactions"]["scope"] == "comment"
    assert row["reactions"].get("commentId") == cid
    summary = {s["emoji"]: s for s in row["reactions"]["summary"]}
    assert summary["🎉"]["count"] >= 1
    assert summary["🎉"]["myReacted"] is True


# ---------------------------------------------------------------------------
# C: unread-count + mark-read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_unread_count_and_mark_read(test_client: AsyncClient):
    user = await _register(test_client, "e52ur")
    issue = await _create_issue(test_client, user)
    await _watch(test_client, user, issue["id"])
    await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "in_progress"},
    )

    unread = await test_client.get(
        "/api/issues/activity/unread-count",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"watching": True},
    )
    assert unread.status_code == 200, unread.text
    body = unread.json()["data"]
    assert body["count"] >= 1
    assert body.get("capped") is False

    marked = await test_client.post(
        "/api/issues/activity/mark-read",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"watching": True},
    )
    assert marked.status_code == 200, marked.text

    unread2 = await test_client.get(
        "/api/issues/activity/unread-count",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"watching": True},
    )
    assert unread2.status_code == 200, unread2.text
    assert unread2.json()["data"]["count"] == 0


@pytest.mark.asyncio
async def test_activity_unread_cross_tenant(test_client: AsyncClient):
    u1 = await _register(test_client, "e52uc1")
    u2 = await _register(test_client, "e52uc2")
    issue = await _create_issue(test_client, u1)
    await _watch(test_client, u1, issue["id"])
    await test_client.put(
        f"/api/issues/{issue['id']}/status",
        headers=_auth(u1["token"], u1["workspaceId"]),
        params={"status": "closed"},
    )
    resp = await test_client.get(
        "/api/issues/activity/unread-count",
        headers=_auth(u2["token"], u2["workspaceId"]),
        params={"watching": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["count"] == 0


# ---------------------------------------------------------------------------
# G: no-emit on read paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_e52_read_paths_no_emit(test_client: AsyncClient):
    user = await _register(test_client, "e52ne")
    issue = await _create_issue(test_client, user)
    await _watch(test_client, user, issue["id"])
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
        r1 = await test_client.get(
            "/api/issues/activity",
            headers=_auth(user["token"], user["workspaceId"]),
            params={"watching": True},
        )
        assert r1.status_code == 200, r1.text
        r2 = await test_client.get(
            "/api/issues/activity/unread-count",
            headers=_auth(user["token"], user["workspaceId"]),
            params={"watching": True},
        )
        assert r2.status_code == 200, r2.text
        r3 = await test_client.post(
            "/api/issues/activity/mark-read",
            headers=_auth(user["token"], user["workspaceId"]),
            json={"watching": True},
        )
        assert r3.status_code == 200, r3.text
        wh.assert_not_called()
        auto.assert_not_called()
