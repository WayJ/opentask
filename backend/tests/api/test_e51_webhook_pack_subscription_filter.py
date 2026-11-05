"""E51：专用 webhook pack + subscription filter（BE 面）。"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.workspace_webhook.model import WEBHOOK_EVENTS


async def _register(client: AsyncClient, prefix: str = "e51"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "e51-issue", **extra) -> dict:
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


async def _create_cycle(client: AsyncClient, user: dict, name: str = "C-e51") -> dict:
    start = datetime(2026, 11, 4, 0, 0, 0)
    end = start + timedelta(days=14)
    resp = await client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "starts_at": start.isoformat(), "ends_at": end.isoformat()},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"Proj-{uuid.uuid4().hex[:6]}", "description": "e51"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_policy(client: AsyncClient, user: dict, **extra) -> dict:
    body = {
        "name": "E51Pause",
        "startStatuses": ["in_progress"],
        "stopStatuses": ["resolved", "closed"],
        "pauseStatuses": ["feedback"],
        "targetMinutes": 60,
        "notifyAssignee": False,
        "notifyWatchers": False,
        "enabled": True,
        **extra,
    }
    resp = await client.post(
        "/api/sla/policies",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


E51_EVENTS = (
    "issue.cycle_changed",
    "issue.estimate_changed",
    "issue.project_changed",
    "issue.sla_paused",
    "issue.sla_resumed",
)


def test_webhook_events_include_e51_pack():
    for ev in E51_EVENTS:
        assert ev in WEBHOOK_EVENTS


@pytest.mark.asyncio
async def test_create_webhook_accepts_e51_events(test_client: AsyncClient):
    user = await _register(test_client, "e51_ev")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post(
        "/api/webhooks",
        headers=h,
        json={"url": "https://example.com/e51", "events": list(E51_EVENTS)},
    )
    assert resp.status_code == 200, resp.text
    events = resp.json()["data"]["events"]
    for ev in E51_EVENTS:
        assert ev in events


@pytest.mark.asyncio
async def test_create_webhook_rejects_unknown_event(test_client: AsyncClient):
    user = await _register(test_client, "e51_bad")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post(
        "/api/webhooks",
        headers=h,
        json={"url": "https://example.com/bad", "events": ["issue.not_a_real_event"]},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_cycle_estimate_project_fire_dedicated_and_updated(test_client: AsyncClient):
    user = await _register(test_client, "e51_cep")
    h = _auth(user["token"], user["workspaceId"])
    cycle = await _create_cycle(test_client, user)
    project = await _create_project(test_client, user)
    issue = await _create_issue(test_client, user, title="cep-wh")

    await test_client.post(
        "/api/webhooks",
        headers=h,
        json={
            "url": "https://example.com/cep",
            "events": [
                "issue.updated",
                "issue.cycle_changed",
                "issue.estimate_changed",
                "issue.project_changed",
            ],
        },
    )

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch:
        patched = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=h,
            json={
                "cycle_id": cycle["id"],
                "estimate_points": 5,
                "project_id": project["id"],
            },
        )
        assert patched.status_code == 200, patched.text
        types = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.updated" in types
        assert "issue.cycle_changed" in types
        assert "issue.estimate_changed" in types
        assert "issue.project_changed" in types

        def _data(ev: str) -> dict:
            return next(
                c.kwargs.get("data") or {}
                for c in dispatch.await_args_list
                if c.kwargs.get("event_type") == ev
            )

        cyc = _data("issue.cycle_changed")
        assert cyc.get("id") == issue["id"]
        assert cyc.get("to") == cycle["id"]
        assert cyc.get("from") in (None, "")
        assert cyc.get("actorUserId") == user["userId"]

        est = _data("issue.estimate_changed")
        assert est.get("to") == 5.0 or est.get("to") == 5
        assert est.get("from") in (None, "", 0, 0.0)

        proj = _data("issue.project_changed")
        assert proj.get("to") == project["id"]


@pytest.mark.asyncio
async def test_unsubscribed_dedicated_events_not_dispatched(test_client: AsyncClient):
    user = await _register(test_client, "e51_unsub")
    h = _auth(user["token"], user["workspaceId"])
    cycle = await _create_cycle(test_client, user)
    issue = await _create_issue(test_client, user)

    # only issue.updated — dedicated events must not be delivered to this hook
    await test_client.post(
        "/api/webhooks",
        headers=h,
        json={"url": "https://example.com/upd-only", "events": ["issue.updated"]},
    )

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService._deliver",
        new_callable=AsyncMock,
    ) as deliver:
        patched = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=h,
            json={"cycle_id": cycle["id"]},
        )
        assert patched.status_code == 200, patched.text
        # dispatch still called for cycle_changed + updated, but _deliver only for subscribed
        envelopes = []
        for c in deliver.await_args_list:
            # _deliver(hook, envelope, ...)
            args = c.args
            if len(args) >= 2 and isinstance(args[1], dict):
                envelopes.append(args[1])
            elif c.kwargs.get("envelope"):
                envelopes.append(c.kwargs["envelope"])
        types = [e.get("type") for e in envelopes]
        assert "issue.updated" in types
        assert "issue.cycle_changed" not in types


@pytest.mark.asyncio
async def test_sla_pause_resume_fire_webhooks_not_automations(test_client: AsyncClient):
    user = await _register(test_client, "e51_sla")
    h = _auth(user["token"], user["workspaceId"])
    await _create_policy(test_client, user)
    issue = await _create_issue(test_client, user, title="sla-wh")

    await test_client.post(
        "/api/webhooks",
        headers=h,
        json={
            "url": "https://example.com/sla",
            "events": ["issue.sla_paused", "issue.sla_resumed", "issue.status_changed", "issue.updated"],
        },
    )

    # start clock
    start = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert start.status_code == 200, start.text

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch, patch(
        "opentask.services.automation.service.fire_automations",
        new_callable=AsyncMock,
    ) as auto:
        paused = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=h,
            json={"status": "feedback"},
        )
        assert paused.status_code == 200, paused.text
        types = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.sla_paused" in types
        assert "issue.updated" in types
        pause_data = next(
            c.kwargs.get("data") or {}
            for c in dispatch.await_args_list
            if c.kwargs.get("event_type") == "issue.sla_paused"
        )
        assert pause_data.get("id") == issue["id"]
        assert pause_data.get("toStatus") == "feedback"
        assert "policyId" in pause_data
        assert "metric" in pause_data

        auto_types = [
            c.kwargs.get("trigger_type")
            for c in auto.await_args_list
            if c.kwargs.get("trigger_type")
        ]
        assert "issue.sla_paused" not in auto_types

        dispatch.reset_mock()
        auto.reset_mock()
        resumed = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=h,
            json={"status": "in_progress"},
        )
        assert resumed.status_code == 200, resumed.text
        types2 = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.sla_resumed" in types2
        resume_data = next(
            c.kwargs.get("data") or {}
            for c in dispatch.await_args_list
            if c.kwargs.get("event_type") == "issue.sla_resumed"
        )
        assert resume_data.get("id") == issue["id"]
        assert "remainingMinutes" in resume_data
        auto_types2 = [
            c.kwargs.get("trigger_type")
            for c in auto.await_args_list
            if c.kwargs.get("trigger_type")
        ]
        assert "issue.sla_resumed" not in auto_types2


@pytest.mark.asyncio
async def test_webhook_crud_does_not_fire_issue_business_events(test_client: AsyncClient):
    user = await _register(test_client, "e51_crud")
    h = _auth(user["token"], user["workspaceId"])
    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch:
        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={"url": "https://example.com/crud", "events": ["issue.created"]},
        )
        assert created.status_code == 200, created.text
        wid = created.json()["data"]["id"]
        await test_client.patch(
            f"/api/webhooks/{wid}",
            headers=h,
            json={"name": "renamed", "setName": True},
        )
        await test_client.delete(f"/api/webhooks/{wid}", headers=h)
        business = [
            c.kwargs.get("event_type")
            for c in dispatch.await_args_list
            if (c.kwargs.get("event_type") or "").startswith("issue.")
        ]
        assert business == []
