"""E44：Webhook event pack + delivery reliability v1."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from opentask.models.workspace_webhook.model import WEBHOOK_EVENTS, WebhookDeliveryLog
from opentask.repositories.base import SessionCreator


async def _register(client: AsyncClient, prefix: str = "e44"):
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


class _FakeResp:
    def __init__(self, status_code: int = 200, text: str = "ok"):
        self.status_code = status_code
        self.text = text


async def _force_due(webhook_id: str) -> None:
    async with SessionCreator() as session:
        rows = (
            await session.execute(
                select(WebhookDeliveryLog).where(
                    WebhookDeliveryLog.webhook_id == webhook_id,
                    WebhookDeliveryLog.status == "pending_retry",
                )
            )
        ).scalars().all()
        for r in rows:
            r.next_attempt_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()


def test_webhook_events_include_e44_pack():
    assert "issue.assignee_changed" in WEBHOOK_EVENTS
    assert "issue.label_added" in WEBHOOK_EVENTS
    assert "issue.label_removed" in WEBHOOK_EVENTS


@pytest.mark.asyncio
async def test_create_webhook_accepts_new_events(test_client: AsyncClient):
    user = await _register(test_client, "e44_ev")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post(
        "/api/webhooks",
        headers=h,
        json={
            "url": "https://example.com/e44",
            "events": [
                "issue.assignee_changed",
                "issue.label_added",
                "issue.label_removed",
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    events = resp.json()["data"]["events"]
    assert "issue.assignee_changed" in events
    assert "issue.label_added" in events
    assert "issue.label_removed" in events


@pytest.mark.asyncio
async def test_assignee_change_fires_dedicated_and_updated(test_client: AsyncClient):
    owner = await _register(test_client, "e44_asg")
    other = await _register(test_client, "e44_asg2")
    await _add_member(test_client, owner, other, role="member")
    h = _auth(owner["token"], owner["workspaceId"])

    issue = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "assignee-wh",
            "type": "feature",
            "status": "open",
            "priority": "medium",
        },
    )
    assert issue.status_code == 200, issue.text
    issue_id = issue.json()["data"]["id"]

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch:
        await test_client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": "https://example.com/asg",
                "events": ["issue.updated", "issue.assignee_changed"],
            },
        )
        patched = await test_client.put(
            f"/api/issues/{issue_id}",
            headers=h,
            json={"assignee_id": other["userId"]},
        )
        assert patched.status_code == 200, patched.text

        types = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.updated" in types
        assert "issue.assignee_changed" in types
        asg_calls = [
            c
            for c in dispatch.await_args_list
            if c.kwargs.get("event_type") == "issue.assignee_changed"
        ]
        assert asg_calls
        data = asg_calls[0].kwargs.get("data") or {}
        assert data.get("to") == other["userId"]
        assert data.get("from") in (None, "")
        assert data.get("actorUserId") == owner["userId"]
        assert data.get("id") == issue_id


@pytest.mark.asyncio
async def test_label_add_remove_fire_dedicated_only(test_client: AsyncClient):
    user = await _register(test_client, "e44_lbl")
    h = _auth(user["token"], user["workspaceId"])

    issue = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "label-wh",
            "type": "feature",
            "status": "open",
            "priority": "medium",
        },
    )
    assert issue.status_code == 200, issue.text
    issue_id = issue.json()["data"]["id"]

    tag = await test_client.post(
        "/api/tags",
        headers=h,
        json={"name": f"e44-{uuid.uuid4().hex[:6]}", "color": "#336699"},
    )
    assert tag.status_code == 200, tag.text
    tag_id = tag.json()["data"]["id"]

    await test_client.post(
        "/api/webhooks",
        headers=h,
        json={
            "url": "https://example.com/lbl",
            "events": ["issue.label_added", "issue.label_removed", "issue.updated"],
        },
    )

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch:
        add = await test_client.post(
            f"/api/issues/{issue_id}/tags/{tag_id}",
            headers=h,
        )
        assert add.status_code == 200, add.text
        types_add = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.label_added" in types_add
        assert "issue.updated" not in types_add
        added = next(
            c
            for c in dispatch.await_args_list
            if c.kwargs.get("event_type") == "issue.label_added"
        )
        assert added.kwargs["data"]["labelId"] == tag_id
        assert added.kwargs["data"]["id"] == issue_id

        dispatch.reset_mock()
        rem = await test_client.delete(
            f"/api/issues/{issue_id}/tags/{tag_id}",
            headers=h,
        )
        assert rem.status_code == 200, rem.text
        types_rem = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.label_removed" in types_rem
        assert "issue.updated" not in types_rem


@pytest.mark.asyncio
async def test_sync_fail_queues_pending_retry_with_payload(test_client: AsyncClient):
    user = await _register(test_client, "e44_q")
    h = _auth(user["token"], user["workspaceId"])

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls, patch(
        "opentask.services.workspace_webhook.service.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(500, "down"))
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={"url": "https://example.com/fail", "events": ["issue.created"]},
        )
        assert created.status_code == 200, created.text
        wid = created.json()["data"]["id"]

        tested = await test_client.post(f"/api/webhooks/{wid}/test", headers=h)
        assert tested.status_code == 200, tested.text
        assert tested.json()["data"]["success"] is False

        detail = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        deliveries = detail.json()["data"].get("deliveries") or []
        assert deliveries, "expected delivery log"
        pending = [d for d in deliveries if d.get("status") == "pending_retry"]
        assert pending, deliveries
        row = pending[0]
        assert row.get("deliveryId")
        assert row.get("replayable") is True
        assert row.get("nextAttemptAt")
        assert row.get("attempt") >= 1


@pytest.mark.asyncio
async def test_run_due_redelivers_and_succeeds(test_client: AsyncClient):
    user = await _register(test_client, "e44_rd")
    h = _auth(user["token"], user["workspaceId"])

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls, patch(
        "opentask.services.workspace_webhook.service.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        # sync: 2 fails; run-due: 1 success
        inst.post = AsyncMock(
            side_effect=[
                _FakeResp(500, "down"),
                _FakeResp(500, "down"),
                _FakeResp(200, "ok"),
            ]
        )
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={"url": "https://example.com/rd", "events": ["issue.created"]},
        )
        wid = created.json()["data"]["id"]
        await test_client.post(f"/api/webhooks/{wid}/test", headers=h)
        await _force_due(wid)

        tick = await test_client.post("/api/webhooks/run-due-deliveries", headers=h)
        assert tick.status_code == 200, tick.text
        body = tick.json()["data"]
        assert body["processed"] >= 1
        assert body["succeeded"] >= 1

        detail = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        deliveries = detail.json()["data"].get("deliveries") or []
        assert any(
            d.get("status") in ("success", "success_after_retry") and d.get("success")
            for d in deliveries
        )


@pytest.mark.asyncio
async def test_max_attempts_marks_dead_and_retry_replays(test_client: AsyncClient):
    user = await _register(test_client, "e44_dead")
    h = _auth(user["token"], user["workspaceId"])

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls, patch(
        "opentask.services.workspace_webhook.service.asyncio.sleep",
        new_callable=AsyncMock,
    ), patch(
        "opentask.services.workspace_webhook.service.WEBHOOK_DELIVERY_MAX_ATTEMPTS",
        2,
    ):
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        # sync 2 fails → dead immediately when max=2
        inst.post = AsyncMock(return_value=_FakeResp(500, "down"))
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={"url": "https://example.com/dead", "events": ["issue.created"]},
        )
        wid = created.json()["data"]["id"]
        await test_client.post(f"/api/webhooks/{wid}/test", headers=h)

        detail = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        deliveries = detail.json()["data"].get("deliveries") or []
        dead = [d for d in deliveries if d.get("status") == "dead"]
        assert dead, deliveries
        log_id = dead[0]["id"]
        assert dead[0].get("replayable") is True

        # manual retry succeeds
        inst.post = AsyncMock(return_value=_FakeResp(200, "ok"))
        client_cls.return_value = inst
        retried = await test_client.post(
            f"/api/webhooks/{wid}/deliveries/{log_id}/retry",
            headers=h,
        )
        assert retried.status_code == 200, retried.text
        assert retried.json()["data"]["success"] is True


@pytest.mark.asyncio
async def test_retry_no_payload_400_and_cross_ws_404(test_client: AsyncClient):
    user = await _register(test_client, "e44_np")
    other = await _register(test_client, "e44_np2")
    h = _auth(user["token"], user["workspaceId"])
    h_other = _auth(other["token"], other["workspaceId"])

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(200, "ok"))
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={"url": "https://example.com/ok", "events": ["issue.created"]},
        )
        wid = created.json()["data"]["id"]
        await test_client.post(f"/api/webhooks/{wid}/test", headers=h)

        detail = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        deliveries = detail.json()["data"].get("deliveries") or []
        assert deliveries
        log_id = deliveries[0]["id"]
        # success cleared payload → not replayable
        bad = await test_client.post(
            f"/api/webhooks/{wid}/deliveries/{log_id}/retry",
            headers=h,
        )
        assert bad.status_code == 400, bad.text

        cross = await test_client.post(
            f"/api/webhooks/{wid}/deliveries/{log_id}/retry",
            headers=h_other,
        )
        assert cross.status_code == 404


@pytest.mark.asyncio
async def test_run_due_viewer_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "e44_own")
    viewer = await _register(test_client, "e44_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    h_viewer = _auth(viewer["token"], owner["workspaceId"])
    resp = await test_client.post("/api/webhooks/run-due-deliveries", headers=h_viewer)
    assert resp.status_code == 403
