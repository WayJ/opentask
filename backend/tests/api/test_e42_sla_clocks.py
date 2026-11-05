"""E42：SLA clocks v1 — policies, sync, run-due, prefs, webhook."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.notification_preference.model import PREF_KEYS, TYPE_TO_PREF_KEY
from opentask.models.workspace_webhook.model import WEBHOOK_EVENTS


async def _register(test_client: AsyncClient, prefix: str = "e42", *, username: str | None = None):
    uname = username or f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await test_client.post(
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


async def _add_member(test_client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


async def _create_issue(test_client: AsyncClient, user: dict, title: str = "e42-issue", **extra) -> dict:
    payload = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        "reporter_id": user["userId"],
        **extra,
    }
    resp = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _watch(test_client: AsyncClient, user: dict, issue_id: str, workspace_id: str):
    resp = await test_client.post(
        f"/api/issues/{issue_id}/watchers",
        headers=_auth(user["token"], workspace_id),
    )
    assert resp.status_code == 200, resp.text


async def _create_policy(test_client: AsyncClient, user: dict, **extra) -> dict:
    body = {
        "name": "First response",
        "startStatuses": ["in_progress"],
        "stopStatuses": ["resolved", "closed"],
        "targetMinutes": 60,
        "notifyAssignee": True,
        "notifyWatchers": True,
        "enabled": True,
        **extra,
    }
    resp = await test_client.post(
        "/api/sla/policies",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ----- A: prefs + webhook constants -----


def test_pref_keys_and_type_map_include_sla_breached():
    assert "sla_breached" in PREF_KEYS
    assert TYPE_TO_PREF_KEY.get("sla_breached") == "sla_breached"


def test_webhook_events_include_sla_breached():
    assert "issue.sla_breached" in WEBHOOK_EVENTS


@pytest.mark.asyncio
async def test_prefs_default_sla_breached_true(test_client: AsyncClient):
    user = await _register(test_client)
    resp = await test_client.get(
        "/api/inbox/preferences",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["sla_breached"] is True


@pytest.mark.asyncio
async def test_prefs_put_sla_breached(test_client: AsyncClient):
    user = await _register(test_client)
    resp = await test_client.put(
        "/api/inbox/preferences",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"sla_breached": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["sla_breached"] is False


# ----- D: policy CRUD -----


@pytest.mark.asyncio
async def test_policy_crud_owner(test_client: AsyncClient):
    owner = await _register(test_client)
    pol = await _create_policy(test_client, owner, name="P1", targetMinutes=120)
    assert pol["name"] == "P1"
    assert pol["metric"] == "time_in_status"
    assert pol["targetMinutes"] == 120
    assert pol["startStatuses"] == ["in_progress"]
    assert pol["enabled"] is True

    listed = await test_client.get(
        "/api/sla/policies",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200
    rows = listed.json()["data"]["rows"]
    assert any(r["id"] == pol["id"] for r in rows)

    patched = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "P1b", "enabled": False, "targetMinutes": 30},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "P1b"
    assert patched.json()["data"]["enabled"] is False
    assert patched.json()["data"]["targetMinutes"] == 30

    deleted = await test_client.delete(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text
    listed2 = await test_client.get(
        "/api/sla/policies",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert all(r["id"] != pol["id"] for r in listed2.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_policy_validation_and_member_forbidden(test_client: AsyncClient):
    owner = await _register(test_client)
    member = await _register(test_client, prefix="e42m")
    await _add_member(test_client, owner, member, role="member")

    bad_status = await test_client.post(
        "/api/sla/policies",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "x", "startStatuses": ["nope"], "targetMinutes": 10},
    )
    assert bad_status.status_code == 400, bad_status.text

    bad_min = await test_client.post(
        "/api/sla/policies",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "x", "startStatuses": ["open"], "targetMinutes": 0},
    )
    assert bad_min.status_code == 400, bad_min.text

    bad_max = await test_client.post(
        "/api/sla/policies",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "x", "startStatuses": ["open"], "targetMinutes": 10081},
    )
    assert bad_max.status_code == 400, bad_max.text

    empty_start = await test_client.post(
        "/api/sla/policies",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "x", "startStatuses": [], "targetMinutes": 10},
    )
    assert empty_start.status_code == 400, empty_start.text

    forbid = await test_client.post(
        "/api/sla/policies",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"name": "nope", "startStatuses": ["open"], "targetMinutes": 10},
    )
    assert forbid.status_code == 403, forbid.text


@pytest.mark.asyncio
async def test_policy_cross_tenant_404(test_client: AsyncClient):
    a = await _register(test_client, prefix="e42a")
    b = await _register(test_client, prefix="e42b")
    pol = await _create_policy(test_client, a)
    resp = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(b["token"], b["workspaceId"]),
        json={"name": "hack"},
    )
    assert resp.status_code == 404, resp.text


# ----- B: sync clocks -----


@pytest.mark.asyncio
async def test_status_enter_start_creates_running_then_stop_mets(test_client: AsyncClient):
    owner = await _register(test_client)
    pol = await _create_policy(
        test_client,
        owner,
        startStatuses=["in_progress"],
        stopStatuses=["resolved"],
        targetMinutes=60,
    )
    issue = await _create_issue(test_client, owner, status="open")

    empty = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["rows"] == []

    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    rows = clocks.json()["data"]["rows"]
    assert len(rows) == 1
    assert rows[0]["status"] == "running"
    assert rows[0]["policyId"] == pol["id"]
    assert rows[0]["startStatus"] == "in_progress"
    assert rows[0]["deadlineAt"] is not None

    # re-enter start → still one running
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "feedback"},
    )
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    clocks2 = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    running = [r for r in clocks2.json()["data"]["rows"] if r["status"] == "running"]
    # after leaving start without stop, clock still running; re-enter does not double
    assert len(running) == 1

    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "resolved"},
    )
    clocks3 = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    rows3 = clocks3.json()["data"]["rows"]
    assert len(rows3) == 1
    assert rows3[0]["status"] == "met"
    assert rows3[0]["stoppedAt"] is not None


@pytest.mark.asyncio
async def test_create_issue_in_start_starts_clock(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(test_client, owner, startStatuses=["open"], stopStatuses=[], targetMinutes=30)
    issue = await _create_issue(test_client, owner, status="open")
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    rows = clocks.json()["data"]["rows"]
    assert len(rows) == 1
    assert rows[0]["status"] == "running"

    # empty stop → closed-class stops
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "closed"},
    )
    clocks2 = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks2.json()["data"]["rows"][0]["status"] == "met"


@pytest.mark.asyncio
async def test_strict_stop_list_ignores_closed_when_not_listed(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(
        test_client,
        owner,
        startStatuses=["in_progress"],
        stopStatuses=["resolved"],  # closed NOT in stop
        targetMinutes=60,
    )
    issue = await _create_issue(test_client, owner, status="open")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "closed"},
    )
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks.json()["data"]["rows"][0]["status"] == "running"


# ----- C: run-due -----


@pytest.mark.asyncio
async def test_run_due_breaches_and_idempotent(test_client: AsyncClient):
    owner = await _register(test_client)
    member = await _register(test_client, prefix="e42w")
    await _add_member(test_client, owner, member, role="member")
    pol = await _create_policy(
        test_client,
        owner,
        startStatuses=["in_progress"],
        stopStatuses=["resolved"],
        targetMinutes=60,
        notifyAssignee=True,
        notifyWatchers=True,
    )
    issue = await _create_issue(
        test_client, owner, status="open", assignee_id=member["userId"]
    )
    await _watch(test_client, owner, issue["id"], owner["workspaceId"])
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    # force deadline into the past via service/db
    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select, update

    past = datetime.utcnow() - timedelta(minutes=5)
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.deadline_at = past
        await session.commit()
        clock_id = clock.id

    r1 = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r1.status_code == 200, r1.text
    d1 = r1.json()["data"]
    assert d1["scanned"] >= 1
    assert d1["breached"] == 1
    assert d1["notificationsCreated"] >= 1

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert inbox.status_code == 200
    types = [n["type"] for n in inbox.json()["data"]["rows"]]
    assert "sla_breached" in types

    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks.json()["data"]["rows"][0]["status"] == "breached"
    assert clocks.json()["data"]["rows"][0]["id"] == clock_id

    r2 = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    d2 = r2.json()["data"]
    assert d2["breached"] == 0


@pytest.mark.asyncio
async def test_run_due_skips_disabled_policy(test_client: AsyncClient):
    owner = await _register(test_client)
    pol = await _create_policy(
        test_client, owner, startStatuses=["in_progress"], targetMinutes=60
    )
    issue = await _create_issue(test_client, owner)
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"enabled": False},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    past = datetime.utcnow() - timedelta(hours=1)
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.deadline_at = past
        await session.commit()

    r = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r.status_code == 200
    assert r.json()["data"]["breached"] == 0
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks.json()["data"]["rows"][0]["status"] == "running"


@pytest.mark.asyncio
async def test_run_due_respects_pref_off(test_client: AsyncClient):
    owner = await _register(test_client)
    await test_client.put(
        "/api/inbox/preferences",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"sla_breached": False},
    )
    await _create_policy(
        test_client,
        owner,
        startStatuses=["in_progress"],
        targetMinutes=60,
        notifyAssignee=True,
        notifyWatchers=False,
    )
    issue = await _create_issue(
        test_client, owner, assignee_id=owner["userId"]
    )
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    past = datetime.utcnow() - timedelta(hours=1)
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.deadline_at = past
        await session.commit()

    r = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["breached"] == 1
    # assignee==actor skip OR pref off → 0 notifications for owner when actor is owner
    # actor_user_id=None in create → pref off means 0
    assert d["notificationsCreated"] == 0


@pytest.mark.asyncio
async def test_run_due_fires_webhook_when_subscribed(test_client: AsyncClient):
    owner = await _register(test_client)
    wh = await test_client.post(
        "/api/webhooks",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "url": "https://example.com/hook",
            "events": ["issue.sla_breached"],
            "name": "sla",
        },
    )
    assert wh.status_code == 200, wh.text

    await _create_policy(test_client, owner, startStatuses=["in_progress"], targetMinutes=60)
    issue = await _create_issue(test_client, owner)
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    past = datetime.utcnow() - timedelta(hours=1)
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.deadline_at = past
        await session.commit()

    with patch(
        "opentask.services.sla.service.fire_webhooks", new_callable=AsyncMock
    ) as fw:
        r = await test_client.post(
            "/api/sla/run-due",
            headers=_auth(owner["token"], owner["workspaceId"]),
        )
        assert r.status_code == 200
        assert r.json()["data"]["breached"] == 1
        assert fw.await_count >= 1
        kwargs = fw.await_args.kwargs
        assert kwargs["event_type"] == "issue.sla_breached"
        assert kwargs["data"]["policyId"]


@pytest.mark.asyncio
async def test_issue_sla_cross_tenant_404(test_client: AsyncClient):
    a = await _register(test_client, prefix="e42x")
    b = await _register(test_client, prefix="e42y")
    issue = await _create_issue(test_client, a)
    resp = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_run_due_viewer_forbidden(test_client: AsyncClient):
    owner = await _register(test_client)
    viewer = await _register(test_client, prefix="e42v")
    await _add_member(test_client, owner, viewer, role="viewer")
    resp = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 403, resp.text
