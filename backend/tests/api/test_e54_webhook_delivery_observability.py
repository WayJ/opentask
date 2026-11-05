"""E54：Webhook delivery observability — stats + dead-letter · no-emit."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.workspace_webhook.model import WEBHOOK_EVENTS, WebhookDeliveryLog
from opentask.repositories.base import SessionCreator


async def _register(client: AsyncClient, prefix: str = "e54"):
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


class _FakeResp:
    def __init__(self, status_code: int = 200, text: str = "ok"):
        self.status_code = status_code
        self.text = text


async def _seed_log(
    *,
    workspace_id: str,
    webhook_id: str,
    status: str,
    event_type: str = "issue.created",
    latency_ms: int | None = 100,
    created_at: datetime | None = None,
    with_payload: bool = True,
) -> str:
    log_id = str(uuid.uuid4())
    async with SessionCreator() as session:
        row = WebhookDeliveryLog(
            id=log_id,
            webhook_id=webhook_id,
            workspace_id=workspace_id,
            event_type=event_type,
            success=status in ("success", "success_after_retry"),
            status_code=200 if status.startswith("success") else 500,
            attempt=5 if status == "dead" else 1,
            latency_ms=latency_ms,
            error=None if status.startswith("success") else "boom",
            delivery_id=str(uuid.uuid4()),
            payload_json=(
                {"id": "evt", "type": event_type, "data": {}} if with_payload else None
            ),
            status=status,
            max_attempts=5,
            created_at=created_at or datetime.utcnow(),
        )
        session.add(row)
        await session.commit()
    return log_id


async def _create_hook(client: AsyncClient, h: dict, name: str = "e54") -> str:
    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(200, "ok"))
        client_cls.return_value = inst
        created = await client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": f"https://example.com/{name}",
                "events": ["issue.created", "issue.updated"],
                "name": name,
            },
        )
    assert created.status_code == 200, created.text
    return created.json()["data"]["id"]


def test_webhook_events_unchanged_no_new_names():
    assert "issue.cycle_changed" in WEBHOOK_EVENTS
    assert "issue.sla_resumed" in WEBHOOK_EVENTS
    assert len(WEBHOOK_EVENTS) == 14


@pytest.mark.asyncio
async def test_stats_default_window_7d_and_illegal(test_client: AsyncClient):
    user = await _register(test_client, "e54_st")
    h = _auth(user["token"], user["workspaceId"])
    wid = await _create_hook(test_client, h, "st")
    await _seed_log(
        workspace_id=user["workspaceId"], webhook_id=wid, status="success", latency_ms=50
    )
    await _seed_log(
        workspace_id=user["workspaceId"], webhook_id=wid, status="dead", latency_ms=80
    )
    await _seed_log(
        workspace_id=user["workspaceId"],
        webhook_id=wid,
        status="pending_retry",
        latency_ms=None,
    )
    # outside window
    await _seed_log(
        workspace_id=user["workspaceId"],
        webhook_id=wid,
        status="success",
        created_at=datetime.utcnow() - timedelta(days=40),
    )

    resp = await test_client.get("/api/webhooks/stats", headers=h)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["window"] == "7d"
    tot = data["totals"]
    assert tot["success"] == 1
    assert tot["dead"] == 1
    assert tot["pending_retry"] == 1
    assert tot["attempts"] == 3
    assert tot["successRate"] == pytest.approx(1 / 3)
    assert "latencyMs" in tot
    assert "p50" in tot["latencyMs"] and "p95" in tot["latencyMs"]
    assert isinstance(data.get("byWebhook"), list)
    assert any(b["webhookId"] == wid for b in data["byWebhook"])

    single = await test_client.get(f"/api/webhooks/{wid}/stats", headers=h)
    assert single.status_code == 200, single.text
    sdata = single.json()["data"]
    assert sdata["window"] == "7d"
    assert sdata["totals"]["attempts"] == 3

    bad = await test_client.get(
        "/api/webhooks/stats", headers=h, params={"window": "1h"}
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_stats_cross_tenant_404(test_client: AsyncClient):
    a = await _register(test_client, "e54_a")
    b = await _register(test_client, "e54_b")
    ha = _auth(a["token"], a["workspaceId"])
    hb = _auth(b["token"], b["workspaceId"])
    wid = await _create_hook(test_client, ha, "x")
    cross = await test_client.get(f"/api/webhooks/{wid}/stats", headers=hb)
    assert cross.status_code == 404


@pytest.mark.asyncio
async def test_dead_letter_list_only_dead_filter(test_client: AsyncClient):
    user = await _register(test_client, "e54_dl")
    h = _auth(user["token"], user["workspaceId"])
    w1 = await _create_hook(test_client, h, "dl1")
    w2 = await _create_hook(test_client, h, "dl2")
    dead1 = await _seed_log(
        workspace_id=user["workspaceId"],
        webhook_id=w1,
        status="dead",
        event_type="issue.created",
    )
    await _seed_log(
        workspace_id=user["workspaceId"],
        webhook_id=w1,
        status="success",
        event_type="issue.created",
    )
    await _seed_log(
        workspace_id=user["workspaceId"],
        webhook_id=w2,
        status="dead",
        event_type="issue.updated",
    )
    await _seed_log(
        workspace_id=user["workspaceId"],
        webhook_id=w1,
        status="pending_retry",
    )

    resp = await test_client.get("/api/webhooks/dead-letter", headers=h)
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]["rows"]
    assert all(r.get("status") == "dead" for r in rows)
    assert len(rows) == 2
    ids = {r["id"] for r in rows}
    assert dead1 in ids

    filt = await test_client.get(
        "/api/webhooks/dead-letter",
        headers=h,
        params={"webhook_id": w1, "event": "issue.created"},
    )
    assert filt.status_code == 200
    frows = filt.json()["data"]["rows"]
    assert len(frows) == 1
    assert frows[0]["id"] == dead1


@pytest.mark.asyncio
async def test_bulk_retry_cap_and_partial(test_client: AsyncClient):
    user = await _register(test_client, "e54_br")
    h = _auth(user["token"], user["workspaceId"])
    wid = await _create_hook(test_client, h, "br")
    ids = []
    for _ in range(2):
        ids.append(
            await _seed_log(
                workspace_id=user["workspaceId"],
                webhook_id=wid,
                status="dead",
                with_payload=True,
            )
        )
    # one missing id
    missing = str(uuid.uuid4())

    over = await test_client.post(
        "/api/webhooks/dead-letter/retry",
        headers=h,
        json={"deliveryLogIds": [str(uuid.uuid4()) for _ in range(51)]},
    )
    assert over.status_code == 400, over.text

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls, patch(
        "opentask.services.workspace_webhook.service.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(200, "ok"))
        client_cls.return_value = inst

        resp = await test_client.post(
            "/api/webhooks/dead-letter/retry",
            headers=h,
            json={"deliveryLogIds": ids + [missing]},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["succeeded"] == 2
    assert body["failed"] == 1
    assert len(body["results"]) == 3
    by_id = {r["deliveryLogId"]: r for r in body["results"]}
    assert by_id[ids[0]]["ok"] is True
    assert by_id[missing]["ok"] is False


@pytest.mark.asyncio
async def test_single_retry_still_works_and_leaves_dead(test_client: AsyncClient):
    user = await _register(test_client, "e54_sr")
    h = _auth(user["token"], user["workspaceId"])
    wid = await _create_hook(test_client, h, "sr")
    log_id = await _seed_log(
        workspace_id=user["workspaceId"], webhook_id=wid, status="dead"
    )
    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls, patch(
        "opentask.services.workspace_webhook.service.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(200, "ok"))
        client_cls.return_value = inst
        retried = await test_client.post(
            f"/api/webhooks/{wid}/deliveries/{log_id}/retry",
            headers=h,
        )
    assert retried.status_code == 200
    assert retried.json()["data"]["success"] is True
    dl = await test_client.get("/api/webhooks/dead-letter", headers=h)
    assert all(r["id"] != log_id for r in dl.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_stats_and_dead_letter_read_no_emit(test_client: AsyncClient):
    user = await _register(test_client, "e54_ne")
    h = _auth(user["token"], user["workspaceId"])
    await _create_hook(test_client, h, "ne")
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as spy:
        await test_client.get("/api/webhooks/stats", headers=h)
        await test_client.get("/api/webhooks/dead-letter", headers=h)
        spy.assert_not_called()
