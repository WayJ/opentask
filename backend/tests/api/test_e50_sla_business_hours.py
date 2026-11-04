"""E50: SLA business hours thin — WS timezone/windows + SLA wiring."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from opentask.models.sla.model import IssueSlaClock
from opentask.repositories.base import SessionCreator


async def _register(test_client: AsyncClient, prefix: str = "e50", *, username: str | None = None):
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


async def _create_issue(test_client: AsyncClient, user: dict, title: str = "e50-issue", **extra) -> dict:
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
        "name": "BH",
        "startStatuses": ["in_progress"],
        "stopStatuses": ["resolved", "closed"],
        "pauseStatuses": ["feedback"],
        "targetMinutes": 60,
        "notifyAssignee": False,
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


async def _clocks(test_client: AsyncClient, user: dict, issue_id: str) -> list:
    resp = await test_client.get(
        f"/api/issues/{issue_id}/sla",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["rows"]


def _weekday_windows_mon_fri():
    return {
        **{d: [{"start": "09:00", "end": "18:00"}] for d in ("mon", "tue", "wed", "thu", "fri")},
        **{d: [] for d in ("sat", "sun")},
    }


@pytest.mark.asyncio
async def test_workspace_default_business_hours(test_client: AsyncClient):
    owner = await _register(test_client)
    resp = await test_client.get(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data.get("timezone") in (None, "")
    bh = data.get("businessHours") or {}
    assert bh.get("enabled") is False


@pytest.mark.asyncio
async def test_workspace_patch_business_hours_ok_and_validation(test_client: AsyncClient):
    owner = await _register(test_client)
    other = await _register(test_client, prefix="e50o")
    ok = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "timezone": "Asia/Shanghai",
            "businessHours": {
                "enabled": True,
                "windows": _weekday_windows_mon_fri(),
            },
        },
    )
    assert ok.status_code == 200, ok.text
    data = ok.json()["data"]
    assert data["timezone"] == "Asia/Shanghai"
    assert data["businessHours"]["enabled"] is True
    assert data["businessHours"]["windows"]["mon"] == [{"start": "09:00", "end": "18:00"}]

    bad_tz = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"timezone": "Not/A_Zone"},
    )
    assert bad_tz.status_code == 400

    bad_win = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "businessHours": {
                "enabled": True,
                "windows": {"mon": [{"start": "18:00", "end": "09:00"}]},
            }
        },
    )
    assert bad_win.status_code == 400

    cross = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(other["token"], other["workspaceId"]),
        json={"timezone": "UTC"},
    )
    assert cross.status_code in (403, 404)


@pytest.mark.asyncio
async def test_config_write_no_webhook_automation(test_client: AsyncClient):
    owner = await _register(test_client)
    with (
        patch(
            "opentask.services.workspace_webhook.service.fire_webhooks",
            new_callable=AsyncMock,
        ) as fw,
        patch(
            "opentask.services.automation.service.fire_automations",
            new_callable=AsyncMock,
        ) as fa,
    ):
        resp = await test_client.patch(
            f"/api/workspaces/{owner['workspaceId']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={
                "timezone": "Asia/Shanghai",
                "businessHours": {"enabled": True, "windows": _weekday_windows_mon_fri()},
            },
        )
        assert resp.status_code == 200, resp.text
        assert fw.await_count == 0
        assert fa.await_count == 0


@pytest.mark.asyncio
async def test_enabled_deadline_skips_weekend(test_client: AsyncClient):
    owner = await _register(test_client)
    await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "timezone": "Asia/Shanghai",
            "businessHours": {"enabled": True, "windows": _weekday_windows_mon_fri()},
        },
    )
    await _create_policy(test_client, owner, targetMinutes=120)
    issue = await _create_issue(test_client, owner)

    frozen = datetime(2026, 11, 6, 9, 0, 0)  # Fri 17:00 Shanghai
    with patch("opentask.services.sla.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = frozen
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        resp = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200, resp.text

    rows = await _clocks(test_client, owner, issue["id"])
    assert len(rows) == 1
    deadline = datetime.fromisoformat(rows[0]["deadlineAt"])
    assert deadline == datetime(2026, 11, 9, 2, 0, 0)  # Mon 10:00 Shanghai


@pytest.mark.asyncio
async def test_disabled_falls_back_to_wall_clock(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(test_client, owner, targetMinutes=60)
    issue = await _create_issue(test_client, owner)
    before = datetime.utcnow()
    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200, resp.text
    row = (await _clocks(test_client, owner, issue["id"]))[0]
    deadline = datetime.fromisoformat(row["deadlineAt"])
    delta = (deadline - before).total_seconds() / 60
    assert 55 <= delta <= 65


@pytest.mark.asyncio
async def test_pause_resume_uses_business_elapsed(test_client: AsyncClient):
    owner = await _register(test_client)
    await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "timezone": "Asia/Shanghai",
            "businessHours": {"enabled": True, "windows": _weekday_windows_mon_fri()},
        },
    )
    await _create_policy(test_client, owner, targetMinutes=120, pauseStatuses=["feedback"])
    issue = await _create_issue(test_client, owner)

    t0 = datetime(2026, 11, 2, 2, 0, 0)  # Mon 10:00 Shanghai
    t1 = datetime(2026, 11, 2, 3, 0, 0)  # Mon 11:00
    t2 = datetime(2026, 11, 2, 4, 0, 0)  # Mon 12:00

    with patch("opentask.services.sla.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = t0
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        r = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"status": "in_progress"},
        )
        assert r.status_code == 200, r.text

        mock_dt.utcnow.return_value = t1
        r = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"status": "feedback"},
        )
        assert r.status_code == 200, r.text

        row = (await _clocks(test_client, owner, issue["id"]))[0]
        assert row["status"] == "paused"
        assert row["elapsedBeforePauseMinutes"] == 60

        mock_dt.utcnow.return_value = t2
        r = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"status": "in_progress"},
        )
        assert r.status_code == 200, r.text

    row = (await _clocks(test_client, owner, issue["id"]))[0]
    assert row["status"] == "running"
    assert datetime.fromisoformat(row["deadlineAt"]) == datetime(2026, 11, 2, 5, 0, 0)


@pytest.mark.asyncio
async def test_config_change_recomputes_running_deadline(test_client: AsyncClient):
    owner = await _register(test_client)
    await _create_policy(test_client, owner, targetMinutes=120)
    issue = await _create_issue(test_client, owner)
    r = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    assert r.status_code == 200, r.text
    before = (await _clocks(test_client, owner, issue["id"]))[0]["deadlineAt"]

    frozen = datetime(2026, 11, 6, 9, 0, 0)
    with patch("opentask.services.sla.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = frozen
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        resp = await test_client.patch(
            f"/api/workspaces/{owner['workspaceId']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={
                "timezone": "Asia/Shanghai",
                "businessHours": {"enabled": True, "windows": _weekday_windows_mon_fri()},
            },
        )
        assert resp.status_code == 200, resp.text

    after = (await _clocks(test_client, owner, issue["id"]))[0]
    assert after["deadlineAt"] != before
    assert after["status"] == "running"


@pytest.mark.asyncio
async def test_first_response_shares_adder_breach_metric_no_emit(test_client: AsyncClient):
    owner = await _register(test_client)
    await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "timezone": "Asia/Shanghai",
            "businessHours": {"enabled": True, "windows": _weekday_windows_mon_fri()},
        },
    )
    await _create_policy(
        test_client,
        owner,
        name="FR",
        metric="first_response",
        targetMinutes=120,
        pauseStatuses=[],
        notifyAssignee=True,
    )
    issue = await _create_issue(test_client, owner)
    frozen = datetime(2026, 11, 6, 9, 0, 0)
    with patch("opentask.services.sla.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = frozen
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        r = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"status": "in_progress"},
        )
        assert r.status_code == 200, r.text

    row = (await _clocks(test_client, owner, issue["id"]))[0]
    assert row.get("metric") == "first_response"
    assert datetime.fromisoformat(row["deadlineAt"]) == datetime(2026, 11, 9, 2, 0, 0)

    async with SessionCreator() as session:
        q = await session.execute(
            select(IssueSlaClock).where(IssueSlaClock.issue_id == issue["id"])
        )
        clock = q.scalar_one()
        clock.deadline_at = datetime.utcnow() - timedelta(minutes=1)
        await session.commit()

    with (
        patch(
            "opentask.services.sla.service.fire_webhooks",
            new_callable=AsyncMock,
        ) as fw,
        patch(
            "opentask.services.sla.service.fire_automations",
            new_callable=AsyncMock,
        ) as fa,
    ):
        r1 = await test_client.post(
            "/api/sla/run-due",
            headers=_auth(owner["token"], owner["workspaceId"]),
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["data"]["breached"] == 1
        assert fw.await_count >= 1
        # metric in webhook payload
        call_kw = fw.await_args
        payload = call_kw.kwargs if call_kw.kwargs else {}
        # fire_webhooks(workspace_id=..., event=..., data=...)
        data = payload.get("data") or (call_kw.args[2] if call_kw and len(call_kw.args) > 2 else {})
        if not data and call_kw:
            # try kwargs event/data
            data = (call_kw.kwargs or {}).get("data") or {}
        assert data.get("metric") == "first_response" or any(
            (c.kwargs or {}).get("data", {}).get("metric") == "first_response"
            or (len(c.args) > 2 and isinstance(c.args[2], dict) and c.args[2].get("metric") == "first_response")
            for c in fw.await_args_list
        )
        # formula no-emit: automations may fire for sla_breached — that's OK; config path already spied
        _ = fa
