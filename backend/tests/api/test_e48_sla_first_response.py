"""E48：SLA first_response metric + pause/resume timeline（无 webhook/automation）。"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.issue.enums import TimelineAction
from opentask.models.sla.model import SLA_METRICS


async def _register(test_client: AsyncClient, prefix: str = "e48", *, username: str | None = None):
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


async def _create_issue(test_client: AsyncClient, user: dict, title: str = "e48-issue", **extra) -> dict:
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


async def _add_member(test_client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


async def _create_policy(test_client: AsyncClient, user: dict, **extra) -> dict:
    body = {
        "name": "FR",
        "startStatuses": ["in_progress"],
        "stopStatuses": ["resolved", "closed"],
        "pauseStatuses": ["feedback"],
        "targetMinutes": 60,
        "notifyAssignee": True,
        "notifyWatchers": False,
        "enabled": True,
        "metric": "first_response",
        **extra,
    }
    resp = await test_client.post(
        "/api/sla/policies",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _patch_status(test_client: AsyncClient, user: dict, issue_id: str, status: str):
    resp = await test_client.put(
        f"/api/issues/{issue_id}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": status},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _timeline(test_client: AsyncClient, user: dict, issue_id: str) -> list:
    resp = await test_client.get(
        f"/api/issues/{issue_id}/timeline",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    if isinstance(data, dict):
        return data.get("rows") or data.get("items") or data.get("timeline") or []
    return data or []


# ----- constants -----


def test_sla_metrics_includes_first_response():
    assert "first_response" in SLA_METRICS
    assert "time_in_status" in SLA_METRICS


def test_timeline_action_pause_resume_values():
    assert TimelineAction.SLA_PAUSED.value == "sla_paused"
    assert TimelineAction.SLA_RESUMED.value == "sla_resumed"


@pytest.mark.asyncio
async def test_create_first_response_policy_and_reject_bad_metric(test_client: AsyncClient):
    user = await _register(test_client)
    ok = await _create_policy(test_client, user, name="FirstResp")
    assert ok["metric"] == "first_response"

    bad = await test_client.post(
        "/api/sla/policies",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": "Bad",
            "startStatuses": ["in_progress"],
            "metric": "resolution_time",
            "targetMinutes": 30,
        },
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_pause_resume_writes_timeline_without_webhook_automation(test_client: AsyncClient):
    user = await _register(test_client)
    await _create_policy(
        test_client,
        user,
        name="TIS",
        metric="time_in_status",
        pauseStatuses=["feedback"],
    )
    issue = await _create_issue(test_client, user)
    await _patch_status(test_client, user, issue["id"], "in_progress")

    with (
        patch(
            "opentask.services.sla.service.fire_webhooks",
            new_callable=AsyncMock,
        ) as wh,
        patch(
            "opentask.services.sla.service.fire_automations",
            new_callable=AsyncMock,
        ) as auto,
    ):
        await _patch_status(test_client, user, issue["id"], "feedback")
        assert wh.await_count == 0
        assert auto.await_count == 0

        rows = await _timeline(test_client, user, issue["id"])
        paused = [r for r in rows if (r.get("action_type") or r.get("actionType")) == "sla_paused"]
        assert len(paused) >= 1
        ad = paused[0].get("action_data") or paused[0].get("actionData") or {}
        assert ad.get("metric") == "time_in_status"
        assert ad.get("policyId")
        assert "elapsedBeforePauseMinutes" in ad

        await _patch_status(test_client, user, issue["id"], "in_progress")
        assert wh.await_count == 0
        assert auto.await_count == 0
        rows2 = await _timeline(test_client, user, issue["id"])
        resumed = [r for r in rows2 if (r.get("action_type") or r.get("actionType")) == "sla_resumed"]
        assert len(resumed) >= 1
        ad2 = resumed[0].get("action_data") or resumed[0].get("actionData") or {}
        assert "remainingMinutes" in ad2
        assert "newDeadlineAt" in ad2

        await _patch_status(test_client, user, issue["id"], "resolved")
        rows3 = await _timeline(test_client, user, issue["id"])
        # stop/met must not add another pause-class entry beyond the earlier ones
        pause_class = [
            r
            for r in rows3
            if (r.get("action_type") or r.get("actionType")) in ("sla_paused", "sla_resumed")
        ]
        assert len(pause_class) == len(paused) + len(resumed)


@pytest.mark.asyncio
async def test_first_response_met_on_non_creator_comment(test_client: AsyncClient):
    owner = await _register(test_client, prefix="e48o")
    other = await _register(test_client, prefix="e48b")
    await _add_member(test_client, owner, other, role="member")

    await _create_policy(test_client, owner, name="FR1", metric="first_response")
    await _create_policy(
        test_client,
        owner,
        name="TIS1",
        metric="time_in_status",
        pauseStatuses=[],
    )
    issue = await _create_issue(test_client, owner, title="fr-issue")
    await _patch_status(test_client, owner, issue["id"], "in_progress")

    sla = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert sla.status_code == 200, sla.text
    clocks = sla.json()["data"]["rows"]
    assert len(clocks) == 2
    assert {c.get("metric") for c in clocks} == {"first_response", "time_in_status"}
    assert all(c["status"] == "running" for c in clocks)

    # creator self-comment does NOT met first_response
    c1 = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"content": "creator note"},
    )
    assert c1.status_code == 200, c1.text
    sla2 = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    fr = next(c for c in sla2.json()["data"]["rows"] if c.get("metric") == "first_response")
    assert fr["status"] == "running"

    # assignee change does NOT met
    asg = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"assignee_id": other["userId"]},
    )
    assert asg.status_code == 200, asg.text
    sla3 = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    fr3 = next(c for c in sla3.json()["data"]["rows"] if c.get("metric") == "first_response")
    assert fr3["status"] == "running"

    # non-creator comment → met
    c2 = await test_client.post(
        f"/api/issues/{issue['id']}/comments",
        headers=_auth(other["token"], owner["workspaceId"]),
        json={"content": "agent reply"},
    )
    assert c2.status_code == 200, c2.text
    sla4 = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    rows4 = sla4.json()["data"]["rows"]
    fr4 = next(c for c in rows4 if c.get("metric") == "first_response")
    tis4 = next(c for c in rows4 if c.get("metric") == "time_in_status")
    assert fr4["status"] == "met"
    assert fr4.get("stoppedAt")
    assert tis4["status"] == "running"  # dual metric independent


@pytest.mark.asyncio
async def test_first_response_breach_payload_includes_metric(test_client: AsyncClient):
    user = await _register(test_client)
    pol = await _create_policy(
        test_client, user, name="FR-breach", metric="first_response", targetMinutes=60
    )
    issue = await _create_issue(test_client, user)
    await _patch_status(test_client, user, issue["id"], "in_progress")

    # backdate deadline
    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select, update

    async with SessionCreator() as db:
        q = await db.execute(
            select(IssueSlaClock).where(
                IssueSlaClock.issue_id == issue["id"],
                IssueSlaClock.policy_id == pol["id"],
            )
        )
        clock = q.scalar_one()
        clock.deadline_at = datetime.utcnow() - timedelta(minutes=5)
        await db.commit()

    with (
        patch(
            "opentask.services.sla.service.fire_webhooks",
            new_callable=AsyncMock,
        ) as wh,
        patch(
            "opentask.services.sla.service.fire_automations",
            new_callable=AsyncMock,
        ) as auto,
    ):
        rd = await test_client.post(
            "/api/sla/run-due",
            headers=_auth(user["token"], user["workspaceId"]),
        )
        assert rd.status_code == 200, rd.text
        assert rd.json()["data"]["breached"] >= 1
        assert wh.await_count >= 1
        wh_kwargs = wh.await_args.kwargs
        assert wh_kwargs.get("event_type") == "issue.sla_breached"
        assert wh_kwargs["data"].get("metric") == "first_response"
        assert auto.await_count >= 1
        auto_kwargs = auto.await_args.kwargs
        assert auto_kwargs.get("trigger_type") == "issue.sla_breached"
        assert auto_kwargs["event"].get("metric") == "first_response"


@pytest.mark.asyncio
async def test_paused_first_response_skipped_by_run_due(test_client: AsyncClient):
    user = await _register(test_client)
    pol = await _create_policy(
        test_client,
        user,
        name="FR-pause",
        metric="first_response",
        pauseStatuses=["feedback"],
        targetMinutes=60,
    )
    issue = await _create_issue(test_client, user)
    await _patch_status(test_client, user, issue["id"], "in_progress")
    await _patch_status(test_client, user, issue["id"], "feedback")

    from opentask.repositories.base import SessionCreator
    from opentask.models.sla.model import IssueSlaClock
    from sqlalchemy import select

    async with SessionCreator() as db:
        q = await db.execute(
            select(IssueSlaClock).where(
                IssueSlaClock.issue_id == issue["id"],
                IssueSlaClock.policy_id == pol["id"],
            )
        )
        clock = q.scalar_one()
        assert clock.status == "paused"
        clock.deadline_at = datetime.utcnow() - timedelta(minutes=30)
        await db.commit()

    rd = await test_client.post(
        "/api/sla/run-due",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert rd.status_code == 200
    assert rd.json()["data"]["breached"] == 0

    sla = await test_client.get(
        f"/api/issues/{issue['id']}/sla",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    row = next(c for c in sla.json()["data"]["rows"] if c["policyId"] == pol["id"])
    assert row["status"] == "paused"


@pytest.mark.asyncio
async def test_first_response_pause_also_writes_timeline(test_client: AsyncClient):
    user = await _register(test_client)
    await _create_policy(
        test_client,
        user,
        name="FR-tl",
        metric="first_response",
        pauseStatuses=["feedback"],
    )
    issue = await _create_issue(test_client, user)
    await _patch_status(test_client, user, issue["id"], "in_progress")
    await _patch_status(test_client, user, issue["id"], "feedback")
    rows = await _timeline(test_client, user, issue["id"])
    paused = [r for r in rows if (r.get("action_type") or r.get("actionType")) == "sla_paused"]
    assert len(paused) >= 1
    ad = paused[0].get("action_data") or paused[0].get("actionData") or {}
    assert ad.get("metric") == "first_response"
