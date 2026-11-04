"""E45：SLA v2 thin — pause_statuses + paused clock + breach→automation."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.automation.model import TRIGGER_TYPES
from opentask.models.sla.model import CLOCK_STATUSES


async def _register(test_client: AsyncClient, prefix: str = "e45", *, username: str | None = None):
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


async def _create_issue(test_client: AsyncClient, user: dict, title: str = "e45-issue", **extra) -> dict:
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


async def _create_policy(test_client: AsyncClient, user: dict, **extra) -> dict:
    body = {
        "name": "Pauseable",
        "startStatuses": ["in_progress"],
        "stopStatuses": ["resolved", "closed"],
        "targetMinutes": 60,
        "notifyAssignee": True,
        "notifyWatchers": False,
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


# ----- constants / defaults -----


def test_clock_statuses_include_paused():
    assert "paused" in CLOCK_STATUSES


def test_trigger_types_include_issue_sla_breached():
    assert "issue.sla_breached" in TRIGGER_TYPES


@pytest.mark.asyncio
async def test_policy_default_pause_statuses_empty(test_client: AsyncClient):
    owner = await _register(test_client)
    pol = await _create_policy(test_client, owner)
    assert pol.get("pauseStatuses") == []


@pytest.mark.asyncio
async def test_policy_pause_statuses_crud_and_validation(test_client: AsyncClient):
    owner = await _register(test_client)
    other = await _register(test_client, prefix="e45o")

    pol = await _create_policy(
        test_client, owner, pauseStatuses=["feedback"], name="WithPause"
    )
    assert pol["pauseStatuses"] == ["feedback"]

    bad = await test_client.post(
        "/api/sla/policies",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "name": "bad",
            "startStatuses": ["in_progress"],
            "pauseStatuses": ["not_a_status"],
            "targetMinutes": 30,
        },
    )
    assert bad.status_code == 400, bad.text

    patched = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"pauseStatuses": []},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["pauseStatuses"] == []

    cross = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(other["token"], other["workspaceId"]),
        json={"pauseStatuses": ["feedback"]},
    )
    assert cross.status_code == 404, cross.text


# ----- sync pause / resume -----


@pytest.mark.asyncio
async def test_enter_pause_then_run_due_skips_paused(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(
        test_client,
        owner,
        pauseStatuses=["feedback"],
        targetMinutes=60,
    )
    issue = await _create_issue(test_client, owner, status="open")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    # age the segment so elapsed > 0 after pause
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.segment_started_at = datetime.utcnow() - timedelta(minutes=12)
        clock.deadline_at = datetime.utcnow() - timedelta(minutes=1)  # would breach if running
        await session.commit()

    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "feedback"},
    )
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    row = clocks.json()["data"]["rows"][0]
    assert row["status"] == "paused"
    assert row["pausedAt"] is not None
    assert row["elapsedBeforePauseMinutes"] >= 12
    # Q3: old deadline retained while paused
    assert row["deadlineAt"] is not None

    r = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["breached"] == 0

    clocks2 = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks2.json()["data"]["rows"][0]["status"] == "paused"


@pytest.mark.asyncio
async def test_resume_recalculates_deadline(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(
        test_client,
        owner,
        pauseStatuses=["feedback"],
        targetMinutes=60,
    )
    issue = await _create_issue(test_client, owner, status="open")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.segment_started_at = datetime.utcnow() - timedelta(minutes=20)
        await session.commit()

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
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    row = clocks.json()["data"]["rows"][0]
    assert row["status"] == "running"
    assert row["pausedAt"] is None
    assert row["elapsedBeforePauseMinutes"] >= 20
    # remaining ≈ 40 minutes
    deadline = datetime.fromisoformat(row["deadlineAt"])
    remaining = (deadline - datetime.utcnow()).total_seconds() / 60
    assert 35 <= remaining <= 45


@pytest.mark.asyncio
async def test_paused_then_stop_mets(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(
        test_client,
        owner,
        pauseStatuses=["feedback"],
        stopStatuses=["resolved"],
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
        json={"status": "feedback"},
    )
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "resolved"},
    )
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    row = clocks.json()["data"]["rows"][0]
    assert row["status"] == "met"
    assert row["stoppedAt"] is not None


@pytest.mark.asyncio
async def test_stop_priority_over_pause(test_client: AsyncClient):
    """If new status is both stop and pause, stop wins → met."""
    owner = await _register(test_client)
    await _create_policy(
        test_client,
        owner,
        pauseStatuses=["resolved"],
        stopStatuses=["resolved"],
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
        json={"status": "resolved"},
    )
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks.json()["data"]["rows"][0]["status"] == "met"


@pytest.mark.asyncio
async def test_empty_pause_keeps_v1_running_through_feedback(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(test_client, owner, pauseStatuses=[], targetMinutes=60)
    issue = await _create_issue(test_client, owner, status="open")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "feedback"},
    )
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks.json()["data"]["rows"][0]["status"] == "running"


# ----- breach → automation -----


@pytest.mark.asyncio
async def test_run_due_fires_automation_once(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(test_client, owner, targetMinutes=60)

    # create automation: on sla_breached → set_priority urgent
    auto = await test_client.post(
        "/api/automations",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "name": "Escalate SLA",
            "triggerType": "issue.sla_breached",
            "actionType": "set_priority",
            "actionConfig": {"priority": "critical"},
            "enabled": True,
        },
    )
    assert auto.status_code == 200, auto.text

    issue = await _create_issue(test_client, owner, status="open", priority="medium")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    past = datetime.utcnow() - timedelta(minutes=5)
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.deadline_at = past
        await session.commit()

    with patch(
        "opentask.services.sla.service.fire_automations",
        new_callable=AsyncMock,
    ) as spy:
        # also need real fire for priority — so call without mock first path:
        pass

    r1 = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["data"]["breached"] == 1

    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks.json()["data"]["rows"][0]["status"] == "breached"

    detail = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["priority"] == "critical"

    r2 = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["breached"] == 0


@pytest.mark.asyncio
async def test_run_due_automation_failure_isolated(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(test_client, owner, targetMinutes=60)
    issue = await _create_issue(test_client, owner, status="open")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    past = datetime.utcnow() - timedelta(minutes=5)
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.deadline_at = past
        await session.commit()

    with patch(
        "opentask.services.sla.service.fire_automations",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        r = await test_client.post(
            "/api/sla/run-due",
            headers=_auth(owner["token"], owner["workspaceId"]),
        )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["breached"] == 1
    clocks = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert clocks.json()["data"]["rows"][0]["status"] == "breached"


@pytest.mark.asyncio
async def test_resume_then_breach_after_remaining_exhausts(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(
        test_client,
        owner,
        pauseStatuses=["feedback"],
        targetMinutes=30,
    )
    issue = await _create_issue(test_client, owner, status="open")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.segment_started_at = datetime.utcnow() - timedelta(minutes=25)
        await session.commit()

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

    # force remaining deadline into past
    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        assert clock.status == "running"
        clock.deadline_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    r = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r.status_code == 200
    assert r.json()["data"]["breached"] == 1
