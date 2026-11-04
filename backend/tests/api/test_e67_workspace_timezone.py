"""E67: workspace TZ into due reminders + recurrence title."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from opentask.services.issue_recurrence.service import expand_title
from opentask.services.notification.service import NotificationService


async def _register(client: AsyncClient, prefix: str = "e67"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
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


async def _set_tz(client: AsyncClient, user: dict, tz: str) -> None:
    r = await client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"timezone": tz},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["timezone"] == tz


# ---------------------------------------------------------------------------
# Unit: expand_title local_date
# ---------------------------------------------------------------------------


def test_expand_title_local_date_override():
    when = datetime(2026, 11, 5, 16, 30, 0)
    assert expand_title("A {date}", when, local_date=date(2026, 11, 6)) == "A 2026-11-06"
    assert expand_title("B {yyyy-mm-dd}", when, local_date=date(2026, 11, 6)) == "B 2026-11-06"
    # default still uses when.date()
    assert expand_title("C {date}", when) == "C 2026-11-05"


# ---------------------------------------------------------------------------
# B — due reminders local day
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e67_due_reminders_uses_shanghai_local_day(
    test_client: AsyncClient, test_session
):
    """UTC 16:30 → Shanghai next day; due=local today → soon (not overdue)."""
    user = await _register(test_client, "e67_due")
    await _set_tz(test_client, user, "Asia/Shanghai")

    ir = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "e67-due-local",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "assignee_id": user["userId"],
            "due_date": "2026-11-06T00:00:00",
        },
    )
    assert ir.status_code == 200, ir.text

    now = datetime(2026, 11, 5, 16, 30, 0, tzinfo=timezone.utc)
    svc = NotificationService(test_session)
    result = await svc.run_due_reminders(
        workspace_id=user["workspaceId"],
        actor_user_id=user["userId"],
        now_utc=now,
    )
    assert result["remindersCreated"] >= 1
    deliveries = await svc.list_due_reminder_deliveries(
        workspace_id=user["workspaceId"],
        bucket_date=date(2026, 11, 6),
    )
    assert len(deliveries) >= 1
    assert all(d.kind == "soon" for d in deliveries)


@pytest.mark.asyncio
async def test_e67_due_reminders_null_tz_stays_utc_day(
    test_client: AsyncClient, test_session
):
    """timezone unset → same now is still UTC 2026-11-05; due 11-06 is soon."""
    user = await _register(test_client, "e67_utc")
    # default timezone is None/empty — do not set

    ir = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "e67-due-utc",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "assignee_id": user["userId"],
            "due_date": "2026-11-06T00:00:00",
        },
    )
    assert ir.status_code == 200, ir.text

    now = datetime(2026, 11, 5, 16, 30, 0, tzinfo=timezone.utc)
    svc = NotificationService(test_session)
    result = await svc.run_due_reminders(
        workspace_id=user["workspaceId"],
        actor_user_id=user["userId"],
        now_utc=now,
    )
    assert result["remindersCreated"] >= 1
    # bucket is UTC today 2026-11-05
    deliveries = await svc.list_due_reminder_deliveries(
        workspace_id=user["workspaceId"],
        bucket_date=date(2026, 11, 5),
    )
    assert len(deliveries) >= 1


@pytest.mark.asyncio
async def test_e67_due_today_override_still_wins(test_client: AsyncClient, test_session):
    user = await _register(test_client, "e67_ov")
    await _set_tz(test_client, user, "Asia/Shanghai")
    ir = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "e67-override",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "assignee_id": user["userId"],
            "due_date": "2026-11-07T00:00:00",
        },
    )
    assert ir.status_code == 200, ir.text

    now = datetime(2026, 11, 5, 16, 30, 0, tzinfo=timezone.utc)
    svc = NotificationService(test_session)
    # inject today=2026-11-07 explicitly — should win over Shanghai local 11-06
    result = await svc.run_due_reminders(
        workspace_id=user["workspaceId"],
        actor_user_id=user["userId"],
        today=date(2026, 11, 7),
        now_utc=now,
    )
    assert result["remindersCreated"] >= 1
    deliveries = await svc.list_due_reminder_deliveries(
        workspace_id=user["workspaceId"],
        bucket_date=date(2026, 11, 7),
    )
    assert len(deliveries) >= 1


# ---------------------------------------------------------------------------
# C — recurrence title local day
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e67_recurrence_title_uses_local_day(test_client: AsyncClient):
    user = await _register(test_client, "e67_rec")
    await _set_tz(test_client, user, "Asia/Shanghai")
    h = _auth(user["token"], user["workspaceId"])

    # next_run_at already due (UTC naive far past)
    cr = await test_client.post(
        "/api/recurrences",
        headers=h,
        json={
            "titleTemplate": "Daily {date}",
            "interval": "daily",
            "nextRunAt": "2020-01-01T00:00:00",
            "enabled": True,
        },
    )
    assert cr.status_code == 200, cr.text
    rec_id = cr.json()["data"]["id"]
    next_before = cr.json()["data"]["nextRunAt"]

    # Monkeypatch local_today so title date is deterministic regardless of wall clock.
    with patch(
        "opentask.services.issue_recurrence.service.local_today",
        return_value=date(2026, 11, 6),
    ):
        rd = await test_client.post("/api/recurrences/run-due", headers=h)
    assert rd.status_code == 200, rd.text
    data = rd.json()["data"]
    assert data["created"] >= 1
    titles = [i.get("title") for i in data.get("issues") or []]
    # issues may only have id — fetch inbox/issue
    issue_id = (data.get("issues") or [{}])[0].get("id")
    assert issue_id
    got = await test_client.get(f"/api/issues/{issue_id}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["title"] == "Daily 2026-11-06"

    # next_run_at advanced (still present, different from before) — no migration
    gr = await test_client.get(f"/api/recurrences/{rec_id}", headers=h)
    assert gr.status_code == 200, gr.text
    assert gr.json()["data"]["nextRunAt"] != next_before


@pytest.mark.asyncio
async def test_e67_run_due_reminders_no_webhook_fire(test_client: AsyncClient):
    user = await _register(test_client, "e67_wh")
    await _set_tz(test_client, user, "UTC")
    await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "e67-wh",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "assignee_id": user["userId"],
            "due_date": datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
            + "Z",
        },
    )
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        create=True,
    ) as spy:
        # also patch common fire path if imported elsewhere
        with patch(
            "opentask.services.notification.service.fire_webhooks",
            create=True,
            new=spy,
        ):
            r = await test_client.post(
                "/api/inbox/run-due-reminders",
                headers=_auth(user["token"], user["workspaceId"]),
            )
    assert r.status_code == 200, r.text
    assert spy.call_count == 0
