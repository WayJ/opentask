"""E8-S2：Project health updates + watchers + Inbox fanout + timeline"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ph"):
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
        json={"name": name or f"Proj-{uuid.uuid4().hex[:6]}", "description": "ph"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_milestone(client: AsyncClient, user: dict, project_id: str, name: str = "M1", **extra):
    resp = await client.post(
        f"/api/projects/{project_id}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, **extra},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


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
async def test_create_project_auto_watches_creator(test_client: AsyncClient):
    user = await _register(test_client, "ph_aw")
    project = await _create_project(test_client, user)
    resp = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]
    assert isinstance(rows, list)
    assert any(r["user_id"] == user["userId"] for r in rows)


@pytest.mark.asyncio
async def test_watch_unwatch_idempotent(test_client: AsyncClient):
    owner = await _register(test_client, "ph_wo")
    member = await _register(test_client, "ph_wm")
    await _add_member(test_client, owner, member)
    project = await _create_project(test_client, owner)

    # member not watching yet
    listed = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200
    assert all(r["user_id"] != member["userId"] for r in listed.json()["data"])

    w1 = await test_client.post(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w1.status_code == 200, w1.text
    w2 = await test_client.post(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w2.status_code == 200, w2.text  # idempotent

    listed2 = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    ids = [r["user_id"] for r in listed2.json()["data"]]
    assert ids.count(member["userId"]) == 1

    deleted = await test_client.delete(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text
    listed3 = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert all(r["user_id"] != member["userId"] for r in listed3.json()["data"])


@pytest.mark.asyncio
async def test_post_health_updates_cache_and_history(test_client: AsyncClient):
    user = await _register(test_client, "ph_hc")
    project = await _create_project(test_client, user)

    post = await test_client.post(
        f"/api/projects/{project['id']}/health",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": "at_risk", "note": "Blocked on API"},
    )
    assert post.status_code == 200, post.text
    data = post.json()["data"]
    assert data["status"] == "at_risk"
    assert data["note"] == "Blocked on API"
    assert data["project_id"] == project["id"]
    assert data["actor_user_id"] == user["userId"]

    detail = await test_client.get(
        f"/api/projects/{project['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert detail.status_code == 200, detail.text
    proj = detail.json()["data"]
    assert proj["health_status"] == "at_risk"
    assert proj["health_note"] == "Blocked on API"
    assert proj.get("health_updated_by") == user["userId"]
    assert proj.get("health_updated_at")

    hist = await test_client.get(
        f"/api/projects/{project['id']}/health",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"history": "1"},
    )
    assert hist.status_code == 200, hist.text
    payload = hist.json()["data"]
    assert payload["latest"]["status"] == "at_risk"
    assert len(payload["history"]) >= 1
    assert payload["history"][0]["note"] == "Blocked on API"


@pytest.mark.asyncio
async def test_health_fanout_inbox_skips_actor(test_client: AsyncClient):
    owner = await _register(test_client, "ph_fo")
    member = await _register(test_client, "ph_fm")
    await _add_member(test_client, owner, member)
    project = await _create_project(test_client, owner)

    # member watches
    watch = await test_client.post(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert watch.status_code == 200, watch.text

    post = await test_client.post(
        f"/api/projects/{project['id']}/health",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "off_track", "note": "Slip"},
    )
    assert post.status_code == 200, post.text

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert inbox.status_code == 200, inbox.text
    rows = inbox.json()["data"]["rows"]
    hits = [
        r
        for r in rows
        if r["type"] == "project_health" and r["resourceId"] == project["id"]
    ]
    assert len(hits) >= 1
    assert hits[0]["resourceType"] == "project"
    assert "off_track" in (hits[0]["title"] or "").lower() or "偏离" in (hits[0]["title"] or "") or "风险" in (hits[0]["title"] or "") or "健康" in (hits[0]["title"] or "") or "off" in (hits[0]["title"] or "").lower()

    own = await test_client.get(
        "/api/inbox",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert own.status_code == 200
    own_hits = [
        r
        for r in own.json()["data"]["rows"]
        if r["type"] == "project_health" and r["resourceId"] == project["id"]
    ]
    assert own_hits == []


@pytest.mark.asyncio
async def test_health_invalid_status_400(test_client: AsyncClient):
    user = await _register(test_client, "ph_bad")
    project = await _create_project(test_client, user)
    resp = await test_client.post(
        f"/api/projects/{project['id']}/health",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": "unknown"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_health_viewer_cannot_write(test_client: AsyncClient):
    owner = await _register(test_client, "ph_vo")
    viewer = await _register(test_client, "ph_vv")
    await _add_member(test_client, owner, viewer, role="viewer")
    project = await _create_project(test_client, owner)

    resp = await test_client.post(
        f"/api/projects/{project['id']}/health",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"status": "on_track", "note": "ok"},
    )
    assert resp.status_code == 403

    # viewer can read
    get_resp = await test_client.get(
        f"/api/projects/{project['id']}/health",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert get_resp.status_code == 200, get_resp.text


@pytest.mark.asyncio
async def test_health_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "ph_xa")
    b = await _register(test_client, "ph_xb")
    project = await _create_project(test_client, a)
    resp = await test_client.post(
        f"/api/projects/{project['id']}/health",
        headers=_auth(b["token"], b["workspaceId"]),
        json={"status": "on_track"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_timeline_aggregates_milestones_and_due_issues(test_client: AsyncClient):
    user = await _register(test_client, "ph_tl")
    project = await _create_project(test_client, user)

    # set project dates
    upd = await test_client.put(
        f"/api/projects/{project['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "starts_at": datetime(2026, 11, 1).isoformat(),
            "target_date": datetime(2026, 12, 15).isoformat(),
        },
    )
    assert upd.status_code == 200, upd.text

    await _create_milestone(
        test_client,
        user,
        project["id"],
        name="Ship",
        target_date=datetime(2026, 12, 1).isoformat(),
    )
    due = (datetime.utcnow() + timedelta(days=7)).replace(microsecond=0)
    with_due = await _create_issue(
        test_client,
        user,
        "has-due",
        project_id=project["id"],
        due_date=due.isoformat(),
    )
    await _create_issue(
        test_client,
        user,
        "no-due",
        project_id=project["id"],
    )

    resp = await test_client.get(
        f"/api/projects/{project['id']}/timeline",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["project"]["id"] == project["id"]
    assert data["project"].get("starts_at")
    assert data["project"].get("target_date")
    assert len(data["milestones"]) >= 1
    assert any(m["name"] == "Ship" for m in data["milestones"])
    issue_ids = {i["id"] for i in data["issues"]}
    assert with_due["id"] in issue_ids
    assert all(i.get("due_date") for i in data["issues"])
