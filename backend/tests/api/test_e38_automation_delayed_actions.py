"""E38：Automation delayed actions — enqueue + run-due + dedupe + cancel."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from opentask.models.automation.model import AutomationPendingAction
from opentask.repositories.base import SessionCreator


async def _register(client: AsyncClient, prefix: str = "e38"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "e38-issue", **extra) -> dict:
    payload = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_rule(client: AsyncClient, user: dict, **body) -> dict:
    payload = {
        "name": body.pop("name", "e38-rule"),
        "triggerType": body.pop("triggerType", "issue.created"),
        "actionType": body.pop("actionType", "set_priority"),
        "actionConfig": body.pop("actionConfig", {"priority": "high"}),
        **body,
    }
    resp = await client.post(
        "/api/automations",
        headers=_auth(user["token"], user["workspaceId"]),
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _pending_rows(workspace_id: str) -> list[AutomationPendingAction]:
    async with SessionCreator() as session:
        rows = (
            await session.execute(
                select(AutomationPendingAction).where(
                    AutomationPendingAction.workspace_id == workspace_id
                )
            )
        ).scalars().all()
        # detach fields we need
        out = []
        for r in rows:
            out.append(
                type(
                    "P",
                    (),
                    {
                        "id": r.id,
                        "rule_id": r.rule_id,
                        "issue_id": r.issue_id,
                        "status": r.status,
                        "run_at": r.run_at,
                        "action_type": r.action_type,
                        "action_config_json": dict(r.action_config_json or {}),
                        "workspace_id": r.workspace_id,
                    },
                )()
            )
        return out


@pytest.mark.asyncio
async def test_delay_zero_still_immediate(test_client: AsyncClient):
    user = await _register(test_client, "e38_imm")
    h = _auth(user["token"], user["workspaceId"])
    await _create_rule(
        test_client,
        user,
        name="imm",
        triggerType="issue.created",
        actionType="set_priority",
        actionConfig={"priority": "high", "delay_minutes": 0},
    )
    issue = await _create_issue(test_client, user, title="imm-issue")
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["priority"] == "high"
    rows = await _pending_rows(user["workspaceId"])
    assert rows == []


@pytest.mark.asyncio
async def test_delay_enqueues_without_immediate_exec(test_client: AsyncClient):
    user = await _register(test_client, "e38_enq")
    h = _auth(user["token"], user["workspaceId"])
    rule = await _create_rule(
        test_client,
        user,
        name="delay5",
        triggerType="issue.created",
        actionType="set_priority",
        actionConfig={"priority": "urgent", "delay_minutes": 5},
    )
    before = datetime.utcnow()
    issue = await _create_issue(test_client, user, title="delayed-issue")
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "medium"  # not yet
    rows = await _pending_rows(user["workspaceId"])
    assert len(rows) == 1
    p = rows[0]
    assert p.rule_id == rule["id"]
    assert p.issue_id == issue["id"]
    assert p.status == "pending"
    assert p.action_type == "set_priority"
    assert "delay_minutes" not in p.action_config_json
    assert "delayMinutes" not in p.action_config_json
    assert p.action_config_json.get("priority") == "urgent"
    assert p.run_at >= before + timedelta(minutes=4, seconds=50)
    assert p.run_at <= before + timedelta(minutes=5, seconds=30)


@pytest.mark.asyncio
async def test_delay_minutes_camel_accepted(test_client: AsyncClient):
    user = await _register(test_client, "e38_cam")
    rule = await _create_rule(
        test_client,
        user,
        actionConfig={"priority": "low", "delayMinutes": 10},
    )
    assert rule["actionConfig"].get("delayMinutes") == 10 or rule["actionConfig"].get(
        "delay_minutes"
    ) in (10, None)
    # stored as provided; validation accepted
    issue = await _create_issue(test_client, user, title="camel")
    rows = await _pending_rows(user["workspaceId"])
    assert len(rows) == 1
    assert rows[0].issue_id == issue["id"]


@pytest.mark.asyncio
async def test_invalid_delay_rejected(test_client: AsyncClient):
    user = await _register(test_client, "e38_bad")
    h = _auth(user["token"], user["workspaceId"])
    for bad in (-1, 10081, "x"):
        resp = await test_client.post(
            "/api/automations",
            headers=h,
            json={
                "name": f"bad-{bad}",
                "triggerType": "issue.created",
                "actionType": "set_priority",
                "actionConfig": {"priority": "high", "delay_minutes": bad},
            },
        )
        assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_dedupe_same_rule_issue(test_client: AsyncClient):
    user = await _register(test_client, "e38_ded")
    h = _auth(user["token"], user["workspaceId"])
    await _create_rule(
        test_client,
        user,
        triggerType="issue.status_changed",
        actionType="add_comment",
        actionConfig={"content": "follow-up", "delay_minutes": 30},
    )
    issue = await _create_issue(test_client, user, title="dedupe")
    # first status change → enqueue
    r1 = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert r1.status_code == 200, r1.text
    # second change → should not create second pending
    r2 = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "closed"},
    )
    assert r2.status_code == 200, r2.text
    rows = await _pending_rows(user["workspaceId"])
    pending = [p for p in rows if p.status == "pending"]
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_disable_cancels_pending(test_client: AsyncClient):
    user = await _register(test_client, "e38_dis")
    h = _auth(user["token"], user["workspaceId"])
    rule = await _create_rule(
        test_client,
        user,
        actionConfig={"priority": "high", "delay_minutes": 60},
    )
    await _create_issue(test_client, user, title="to-cancel")
    rows = await _pending_rows(user["workspaceId"])
    assert len(rows) == 1 and rows[0].status == "pending"
    dis = await test_client.post(f"/api/automations/{rule['id']}/disable", headers=h)
    assert dis.status_code == 200, dis.text
    rows2 = await _pending_rows(user["workspaceId"])
    assert len(rows2) == 1
    assert rows2[0].status == "cancelled"


@pytest.mark.asyncio
async def test_run_due_not_yet(test_client: AsyncClient):
    user = await _register(test_client, "e38_ny")
    h = _auth(user["token"], user["workspaceId"])
    await _create_rule(
        test_client,
        user,
        actionConfig={"priority": "high", "delay_minutes": 120},
    )
    issue = await _create_issue(test_client, user, title="not-yet")
    ran = await test_client.post("/api/automations/run-due", headers=h)
    assert ran.status_code == 200, ran.text
    data = ran.json()["data"]
    assert data["processed"] == 0
    assert data["executed"] == 0
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "medium"
    rows = await _pending_rows(user["workspaceId"])
    assert rows[0].status == "pending"


@pytest.mark.asyncio
async def test_run_due_executes_when_due(test_client: AsyncClient):
    user = await _register(test_client, "e38_due")
    h = _auth(user["token"], user["workspaceId"])
    await _create_rule(
        test_client,
        user,
        actionType="set_priority",
        actionConfig={"priority": "high", "delay_minutes": 1},
    )
    issue = await _create_issue(test_client, user, title="due-now")
    # force run_at into the past
    async with SessionCreator() as session:
        row = (
            await session.execute(
                select(AutomationPendingAction).where(
                    AutomationPendingAction.issue_id == issue["id"]
                )
            )
        ).scalar_one()
        row.run_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    ran = await test_client.post("/api/automations/run-due", headers=h)
    assert ran.status_code == 200, ran.text
    data = ran.json()["data"]
    assert data["processed"] == 1
    assert data["executed"] == 1
    assert data["failed"] == 0
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "high"
    rows = await _pending_rows(user["workspaceId"])
    assert rows[0].status == "done"


@pytest.mark.asyncio
async def test_run_due_cancels_when_condition_fails(test_client: AsyncClient):
    user = await _register(test_client, "e38_cond")
    h = _auth(user["token"], user["workspaceId"])
    await _create_rule(
        test_client,
        user,
        triggerType="issue.status_changed",
        actionType="set_priority",
        condition={"statusIn": ["in_progress"]},
        actionConfig={"priority": "high", "delay_minutes": 1},
    )
    issue = await _create_issue(test_client, user, title="cond")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    rows = await _pending_rows(user["workspaceId"])
    assert len(rows) == 1
    # change status so condition no longer matches
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "closed"},
    )
    async with SessionCreator() as session:
        row = (
            await session.execute(
                select(AutomationPendingAction).where(
                    AutomationPendingAction.id == rows[0].id
                )
            )
        ).scalar_one()
        row.run_at = datetime.utcnow() - timedelta(seconds=5)
        await session.commit()

    ran = await test_client.post("/api/automations/run-due", headers=h)
    assert ran.status_code == 200, ran.text
    data = ran.json()["data"]
    assert data["cancelled"] >= 1
    assert data["executed"] == 0
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "medium"


@pytest.mark.asyncio
async def test_run_due_viewer_forbidden_and_cross_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "e38_own")
    viewer = await _register(test_client, "e38_view")
    other = await _register(test_client, "e38_oth")
    await _add_member(test_client, owner, viewer, role="viewer")
    h_viewer = _auth(viewer["token"], owner["workspaceId"])
    h_other = _auth(other["token"], other["workspaceId"])
    h_owner = _auth(owner["token"], owner["workspaceId"])

    await _create_rule(
        test_client,
        owner,
        actionConfig={"priority": "high", "delay_minutes": 1},
    )
    issue = await _create_issue(test_client, owner, title="tenant")
    async with SessionCreator() as session:
        row = (
            await session.execute(
                select(AutomationPendingAction).where(
                    AutomationPendingAction.issue_id == issue["id"]
                )
            )
        ).scalar_one()
        row.run_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    forbidden = await test_client.post("/api/automations/run-due", headers=h_viewer)
    assert forbidden.status_code == 403, forbidden.text

    # other WS tick must not execute owner's pending
    cross = await test_client.post("/api/automations/run-due", headers=h_other)
    assert cross.status_code == 200, cross.text
    assert cross.json()["data"]["processed"] == 0

    listed = await test_client.get("/api/automations/pending", headers=h_owner)
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["total"] >= 1

    # viewer can list? design: member+ for write; list is member+ suggested — require writer
    listed_v = await test_client.get("/api/automations/pending", headers=h_viewer)
    # design: viewer 读规则 OK、run-due/写 pending 403 — list pending 属写面 → 403
    assert listed_v.status_code == 403, listed_v.text


@pytest.mark.asyncio
async def test_run_due_fail_isolates(test_client: AsyncClient):
    user = await _register(test_client, "e38_iso")
    h = _auth(user["token"], user["workspaceId"])
    # good rule
    await _create_rule(
        test_client,
        user,
        name="good",
        actionType="set_priority",
        actionConfig={"priority": "high", "delay_minutes": 1},
    )
    # bad rule: set_status without status → will fail at execute
    await _create_rule(
        test_client,
        user,
        name="bad",
        actionType="set_status",
        actionConfig={"delay_minutes": 1},  # missing status
    )
    issue = await _create_issue(test_client, user, title="iso")
    async with SessionCreator() as session:
        rows = (
            await session.execute(
                select(AutomationPendingAction).where(
                    AutomationPendingAction.workspace_id == user["workspaceId"]
                )
            )
        ).scalars().all()
        assert len(rows) == 2
        for row in rows:
            row.run_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    ran = await test_client.post("/api/automations/run-due", headers=h)
    assert ran.status_code == 200, ran.text
    data = ran.json()["data"]
    assert data["processed"] == 2
    assert data["executed"] == 1
    assert data["failed"] == 1
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "high"
