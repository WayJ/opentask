"""E35：Recurring Issues CRUD + run-due + 租户."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "rc"):
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


async def _add_member(client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_recurrence_crud(test_client: AsyncClient):
    user = await _register(test_client, "rc_crud")
    h = _auth(user["token"], user["workspaceId"])
    past = (datetime.utcnow() - timedelta(hours=1)).isoformat()

    created = await test_client.post(
        "/api/recurrences",
        headers=h,
        json={
            "titleTemplate": "Daily standup {date}",
            "interval": "daily",
            "nextRunAt": past,
            "priority": "high",
            "labels": ["ops"],
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["titleTemplate"] == "Daily standup {date}"
    assert row["interval"] == "daily"
    assert row["enabled"] is True
    rid = row["id"]

    listed = await test_client.get("/api/recurrences", headers=h)
    assert listed.status_code == 200, listed.text
    assert any(r["id"] == rid for r in listed.json()["data"]["rows"])

    got = await test_client.get(f"/api/recurrences/{rid}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["id"] == rid

    patched = await test_client.patch(
        f"/api/recurrences/{rid}",
        headers=h,
        json={"enabled": False, "titleTemplate": "Standup {yyyy-mm-dd}"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["enabled"] is False
    assert "yyyy-mm-dd" in patched.json()["data"]["titleTemplate"]

    deleted = await test_client.delete(f"/api/recurrences/{rid}", headers=h)
    assert deleted.status_code == 200, deleted.text
    missing = await test_client.get(f"/api/recurrences/{rid}", headers=h)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_recurrence_viewer_and_cross_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "rc_own")
    viewer = await _register(test_client, "rc_view")
    other = await _register(test_client, "rc_oth")
    await _add_member(test_client, owner, viewer, role="viewer")

    h_owner = _auth(owner["token"], owner["workspaceId"])
    past = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
    created = await test_client.post(
        "/api/recurrences",
        headers=h_owner,
        json={
            "titleTemplate": "x {date}",
            "interval": "weekly",
            "weekday": 0,
            "nextRunAt": past,
        },
    )
    assert created.status_code == 200, created.text
    rid = created.json()["data"]["id"]

    h_viewer = _auth(viewer["token"], owner["workspaceId"])
    listed = await test_client.get("/api/recurrences", headers=h_viewer)
    assert listed.status_code == 200, listed.text

    forbidden = await test_client.post(
        "/api/recurrences",
        headers=h_viewer,
        json={"titleTemplate": "nope", "interval": "daily", "nextRunAt": past},
    )
    assert forbidden.status_code == 403

    run_forbidden = await test_client.post("/api/recurrences/run-due", headers=h_viewer)
    assert run_forbidden.status_code == 403

    h_other = _auth(other["token"], other["workspaceId"])
    cross = await test_client.get(f"/api/recurrences/{rid}", headers=h_other)
    assert cross.status_code == 404

    cross_run = await test_client.post("/api/recurrences/run-due", headers=h_other)
    assert cross_run.status_code == 200
    assert cross_run.json()["data"]["created"] == 0


@pytest.mark.asyncio
async def test_run_due_creates_issue_and_advances(test_client: AsyncClient):
    user = await _register(test_client, "rc_run")
    h = _auth(user["token"], user["workspaceId"])
    past = (datetime.utcnow() - timedelta(hours=2)).isoformat()

    created = await test_client.post(
        "/api/recurrences",
        headers=h,
        json={
            "titleTemplate": "Backup {yyyy-mm-dd}",
            "interval": "daily",
            "nextRunAt": past,
            "description": "auto",
            "priority": "medium",
        },
    )
    assert created.status_code == 200, created.text
    rid = created.json()["data"]["id"]
    old_next = created.json()["data"]["nextRunAt"]

    ran = await test_client.post("/api/recurrences/run-due", headers=h)
    assert ran.status_code == 200, ran.text
    data = ran.json()["data"]
    assert data["created"] == 1
    assert len(data["issues"]) == 1
    issue = data["issues"][0]
    assert issue["recurrenceId"] == rid
    assert "Backup " in issue["title"]
    # placeholder expanded to YYYY-MM-DD
    assert len(issue["title"].split()[-1]) == 10

    got = await test_client.get(f"/api/recurrences/{rid}", headers=h)
    assert got.status_code == 200, got.text
    row = got.json()["data"]
    assert row["lastIssueId"] == issue["id"]
    assert row["nextRunAt"] != old_next
    # next should be in the future relative to now
    assert datetime.fromisoformat(row["nextRunAt"]) > datetime.utcnow() - timedelta(seconds=5)

    # second tick with future next → 0 created
    ran2 = await test_client.post("/api/recurrences/run-due", headers=h)
    assert ran2.status_code == 200, ran2.text
    assert ran2.json()["data"]["created"] == 0

    # issue exists
    detail = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=h,
    )
    assert detail.status_code == 200, detail.text
    assert "Backup " in detail.json()["data"]["title"]


@pytest.mark.asyncio
async def test_run_due_disabled_skipped(test_client: AsyncClient):
    user = await _register(test_client, "rc_dis")
    h = _auth(user["token"], user["workspaceId"])
    past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    created = await test_client.post(
        "/api/recurrences",
        headers=h,
        json={
            "titleTemplate": "off {date}",
            "interval": "daily",
            "nextRunAt": past,
            "enabled": False,
        },
    )
    assert created.status_code == 200, created.text
    ran = await test_client.post("/api/recurrences/run-due", headers=h)
    assert ran.status_code == 200, ran.text
    assert ran.json()["data"]["created"] == 0


@pytest.mark.asyncio
async def test_expand_title_unit():
    from opentask.services.issue_recurrence.service import expand_title

    when = datetime(2026, 11, 4, 12, 0, 0)
    assert expand_title("A {date}", when) == "A 2026-11-04"
    assert expand_title("B {yyyy-mm-dd}", when) == "B 2026-11-04"
