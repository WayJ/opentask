"""E57：Webhook dead-letter alerts — settings / eval / autoDisable / no-emit."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from opentask.models.notification.model import Notification
from opentask.models.workspace_webhook.model import WEBHOOK_EVENTS, WebhookDeliveryLog
from opentask.repositories.base import SessionCreator


async def _register(client: AsyncClient, prefix: str = "e57"):
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
    created_at: datetime | None = None,
) -> str:
    log_id = str(uuid.uuid4())
    async with SessionCreator() as session:
        row = WebhookDeliveryLog(
            id=log_id,
            webhook_id=webhook_id,
            workspace_id=workspace_id,
            event_type="issue.created",
            success=status in ("success", "success_after_retry"),
            status_code=200 if status.startswith("success") else 500,
            attempt=5 if status == "dead" else 1,
            latency_ms=100,
            error=None if status.startswith("success") else "boom",
            delivery_id=str(uuid.uuid4()),
            payload_json={"id": "evt", "type": "issue.created", "data": {}},
            status=status,
            max_attempts=5,
            created_at=created_at or datetime.utcnow(),
        )
        session.add(row)
        await session.commit()
    return log_id


async def _create_hook(client: AsyncClient, h: dict, name: str = "e57") -> str:
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
                "url": f"https://example.com/{name}-{uuid.uuid4().hex[:6]}",
                "events": ["issue.created"],
                "name": name,
            },
        )
    assert created.status_code == 200, created.text
    return created.json()["data"]["id"]


def test_webhook_events_unchanged_no_new_names():
    assert len(WEBHOOK_EVENTS) == 14
    assert "webhook_dead_letter_alert" not in WEBHOOK_EVENTS


@pytest.mark.asyncio
async def test_default_opt_in_off_never_alerts(test_client: AsyncClient):
    user = await _register(test_client, "e57_off")
    h = _auth(user["token"], user["workspaceId"])
    wid = await _create_hook(test_client, h, "off")
    for _ in range(12):
        await _seed_log(workspace_id=user["workspaceId"], webhook_id=wid, status="dead")

    show = await test_client.get("/api/webhooks/alerts", headers=h)
    assert show.status_code == 200, show.text
    assert show.json()["data"]["settings"]["enabled"] is False

    with patch(
        "opentask.services.workspace_webhook.alerts.fire_webhooks", create=True
    ) as fw:
        # ensure evaluate path itself doesn't import fire; spy via service module
        pass
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        ev = await test_client.post("/api/webhooks/run-alert-eval", headers=h)
        assert ev.status_code == 200, ev.text
        data = ev.json()["data"]
        assert data.get("skippedMasterOff") == 1
        assert data.get("alerts", 0) == 0
        fw.assert_not_called()

    async with SessionCreator() as session:
        n = (
            await session.execute(
                select(Notification).where(
                    Notification.workspace_id == user["workspaceId"],
                    Notification.type == "webhook_dead_letter_alert",
                )
            )
        ).scalars().all()
    assert len(n) == 0


@pytest.mark.asyncio
async def test_threshold_boundary_dedup_and_mute(test_client: AsyncClient):
    user = await _register(test_client, "e57_th")
    h = _auth(user["token"], user["workspaceId"])
    wid = await _create_hook(test_client, h, "th")

    bad = await test_client.patch(
        "/api/webhooks/alerts",
        headers=h,
        json={"settings": {"enabled": True, "windowHours": 0, "deadThreshold": 3}},
    )
    assert bad.status_code == 400

    ok = await test_client.patch(
        "/api/webhooks/alerts",
        headers=h,
        json={
            "settings": {
                "enabled": True,
                "windowHours": 24,
                "deadThreshold": 3,
                "autoDisable": False,
            }
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["settings"]["enabled"] is True

    for _ in range(2):
        await _seed_log(workspace_id=user["workspaceId"], webhook_id=wid, status="dead")
    ev1 = await test_client.post("/api/webhooks/run-alert-eval", headers=h)
    assert ev1.status_code == 200
    assert ev1.json()["data"].get("alerts", 0) == 0

    await _seed_log(workspace_id=user["workspaceId"], webhook_id=wid, status="dead")
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        ev2 = await test_client.post("/api/webhooks/run-alert-eval", headers=h)
        assert ev2.status_code == 200, ev2.text
        assert ev2.json()["data"]["alerts"] >= 1
        fw.assert_not_called()

    async with SessionCreator() as session:
        n1 = list(
            (
                await session.execute(
                    select(Notification).where(
                        Notification.workspace_id == user["workspaceId"],
                        Notification.type == "webhook_dead_letter_alert",
                    )
                )
            ).scalars().all()
        )
    assert len(n1) >= 1
    count_after_first = len(n1)

    # same bucket more dead → no new alert
    await _seed_log(workspace_id=user["workspaceId"], webhook_id=wid, status="dead")
    ev3 = await test_client.post("/api/webhooks/run-alert-eval", headers=h)
    assert ev3.status_code == 200
    async with SessionCreator() as session:
        n2 = list(
            (
                await session.execute(
                    select(Notification).where(
                        Notification.workspace_id == user["workspaceId"],
                        Notification.type == "webhook_dead_letter_alert",
                    )
                )
            ).scalars().all()
        )
    assert len(n2) == count_after_first

    # mute
    until = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    mute = await test_client.post(
        "/api/webhooks/alerts/mute", headers=h, json={"until": until}
    )
    assert mute.status_code == 200, mute.text
    assert mute.json()["data"]["settings"]["muteUntil"]


@pytest.mark.asyncio
async def test_auto_disable_and_manual_reenable(test_client: AsyncClient):
    user = await _register(test_client, "e57_ad")
    h = _auth(user["token"], user["workspaceId"])
    wid = await _create_hook(test_client, h, "ad")

    await test_client.patch(
        "/api/webhooks/alerts",
        headers=h,
        json={
            "settings": {
                "enabled": True,
                "windowHours": 24,
                "deadThreshold": 2,
                "consecutiveDeadThreshold": 2,
                "autoDisable": True,
            }
        },
    )
    await _seed_log(workspace_id=user["workspaceId"], webhook_id=wid, status="dead")
    await _seed_log(workspace_id=user["workspaceId"], webhook_id=wid, status="dead")
    ev = await test_client.post("/api/webhooks/run-alert-eval", headers=h)
    assert ev.status_code == 200, ev.text
    assert ev.json()["data"].get("autoDisabled", 0) >= 1

    got = await test_client.get(f"/api/webhooks/{wid}", headers=h)
    assert got.status_code == 200
    data = got.json()["data"]
    assert data["enabled"] is False
    assert data["pausedReason"] == "auto_dead_letter_alert"

    dl = await test_client.get("/api/webhooks/dead-letter", headers=h)
    assert dl.status_code == 200
    rows = dl.json()["data"]["rows"]
    assert any(r.get("autoDisabled") for r in rows)

    re = await test_client.patch(
        f"/api/webhooks/{wid}", headers=h, json={"enabled": True}
    )
    assert re.status_code == 200
    assert re.json()["data"]["enabled"] is True
    assert re.json()["data"]["pausedReason"] is None


@pytest.mark.asyncio
async def test_hook_overlay_and_cross_tenant_404(test_client: AsyncClient):
    a = await _register(test_client, "e57_a")
    b = await _register(test_client, "e57_b")
    ha = _auth(a["token"], a["workspaceId"])
    hb = _auth(b["token"], b["workspaceId"])
    wid = await _create_hook(test_client, ha, "ov")

    await test_client.patch(
        "/api/webhooks/alerts",
        headers=ha,
        json={"settings": {"enabled": True, "deadThreshold": 10}},
    )
    ov = await test_client.patch(
        "/api/webhooks/alerts",
        headers=ha,
        json={"webhookId": wid, "settings": {"deadThreshold": 5}},
    )
    assert ov.status_code == 200, ov.text
    assert ov.json()["data"]["effective"]["deadThreshold"] == 5
    assert ov.json()["data"]["settings"]["deadThreshold"] == 10

    # cross-tenant: B cannot read A's hook overlay
    cross = await test_client.get(
        f"/api/webhooks/alerts?webhook_id={wid}", headers=hb
    )
    assert cross.status_code == 404


@pytest.mark.asyncio
async def test_per_hook_alert_settings_via_patch_webhook(test_client: AsyncClient):
    user = await _register(test_client, "e57_ph")
    h = _auth(user["token"], user["workspaceId"])
    wid = await _create_hook(test_client, h, "ph")
    resp = await test_client.patch(
        f"/api/webhooks/{wid}",
        headers=h,
        json={"alertSettings": {"deadThreshold": 7}, "setAlertSettings": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["alertSettings"]["deadThreshold"] == 7
