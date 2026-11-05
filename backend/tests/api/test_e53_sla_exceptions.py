"""E53: SLA business-hours exceptions — WS CRUD + clock wiring."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(test_client: AsyncClient, prefix: str = "e53", *, username: str | None = None):
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


async def _create_issue(test_client: AsyncClient, user: dict, title: str = "e53-issue", **extra) -> dict:
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
        "name": "EX",
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


async def _enable_bh(test_client, user, *, exceptions=None):
    body = {
        "timezone": "Asia/Shanghai",
        "businessHours": {
            "enabled": True,
            "windows": _weekday_windows_mon_fri(),
            "exceptions": exceptions or [],
        },
    }
    resp = await test_client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_patch_exceptions_crud_and_validation(test_client: AsyncClient):
    owner = await _register(test_client)
    other = await _register(test_client, prefix="e53o")
    ok = await _enable_bh(
        test_client,
        owner,
        exceptions=[
            {"date": "2026-11-06", "kind": "closed"},
            {
                "date": "2026-11-07",
                "kind": "forced_open",
                "windows": [{"start": "10:00", "end": "14:00"}],
            },
        ],
    )
    ex = ok["businessHours"]["exceptions"]
    assert {"date": "2026-11-06", "kind": "closed"} in ex
    forced = next(e for e in ex if e["date"] == "2026-11-07")
    assert forced["kind"] == "forced_open"
    assert forced["windows"] == [{"start": "10:00", "end": "14:00"}]

    dup = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "businessHours": {
                "enabled": True,
                "windows": _weekday_windows_mon_fri(),
                "exceptions": [
                    {"date": "2026-11-06", "kind": "closed"},
                    {"date": "2026-11-06", "kind": "forced_open"},
                ],
            }
        },
    )
    assert dup.status_code == 400

    bad_kind = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "businessHours": {
                "enabled": True,
                "windows": _weekday_windows_mon_fri(),
                "exceptions": [{"date": "2026-11-08", "kind": "holiday"}],
            }
        },
    )
    assert bad_kind.status_code == 400

    bad_date = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "businessHours": {
                "enabled": True,
                "windows": _weekday_windows_mon_fri(),
                "exceptions": [{"date": "2026-13-40", "kind": "closed"}],
            }
        },
    )
    assert bad_date.status_code == 400

    cross = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(other["token"], other["workspaceId"]),
        json={
            "businessHours": {
                "enabled": True,
                "windows": _weekday_windows_mon_fri(),
                "exceptions": [{"date": "2026-12-01", "kind": "closed"}],
            }
        },
    )
    assert cross.status_code in (403, 404)


@pytest.mark.asyncio
async def test_closed_day_skips_deadline(test_client: AsyncClient):
    owner = await _register(test_client)
    await _enable_bh(
        test_client,
        owner,
        exceptions=[{"date": "2026-11-06", "kind": "closed"}],  # Fri
    )
    await _create_policy(test_client, owner, targetMinutes=120)
    issue = await _create_issue(test_client, owner)

    # Thu 2026-11-05 17:00 Shanghai = UTC 09:00; Fri closed → Mon 10:00
    frozen = datetime(2026, 11, 5, 9, 0, 0)
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
    assert deadline == datetime(2026, 11, 9, 2, 0, 0)


@pytest.mark.asyncio
async def test_forced_open_counts_on_weekend(test_client: AsyncClient):
    owner = await _register(test_client)
    await _enable_bh(
        test_client,
        owner,
        exceptions=[{"date": "2026-11-07", "kind": "forced_open"}],  # Sat
    )
    await _create_policy(test_client, owner, targetMinutes=60)
    issue = await _create_issue(test_client, owner)

    # Sat 10:00 Shanghai = UTC 02:00; +60 → 11:00 = UTC 03:00
    frozen = datetime(2026, 11, 7, 2, 0, 0)
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
    assert datetime.fromisoformat(rows[0]["deadlineAt"]) == datetime(2026, 11, 7, 3, 0, 0)


@pytest.mark.asyncio
async def test_enabled_false_exceptions_inert(test_client: AsyncClient):
    owner = await _register(test_client)
    resp = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "timezone": "Asia/Shanghai",
            "businessHours": {
                "enabled": False,
                "windows": _weekday_windows_mon_fri(),
                "exceptions": [{"date": "2026-11-06", "kind": "closed"}],
            },
        },
    )
    assert resp.status_code == 200, resp.text
    await _create_policy(test_client, owner, targetMinutes=60)
    issue = await _create_issue(test_client, owner)
    before = datetime.utcnow()
    r = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "in_progress"},
    )
    assert r.status_code == 200, r.text
    row = (await _clocks(test_client, owner, issue["id"]))[0]
    deadline = datetime.fromisoformat(row["deadlineAt"])
    delta = (deadline - before).total_seconds() / 60
    assert 55 <= delta <= 65


@pytest.mark.asyncio
async def test_config_change_recomputes_with_exceptions(test_client: AsyncClient):
    owner = await _register(test_client)
    # Enable BH without exceptions first
    await _enable_bh(test_client, owner, exceptions=[])
    await _create_policy(test_client, owner, targetMinutes=120)
    issue = await _create_issue(test_client, owner)

    frozen = datetime(2026, 11, 5, 9, 0, 0)  # Thu 17:00 CST
    with patch("opentask.services.sla.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = frozen
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        r = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"status": "in_progress"},
        )
        assert r.status_code == 200, r.text
        # Without Fri closed: Thu 60 + Fri 60 → Fri 10:00 CST = UTC 02:00 on 11-06
        before = (await _clocks(test_client, owner, issue["id"]))[0]["deadlineAt"]
        assert datetime.fromisoformat(before) == datetime(2026, 11, 6, 2, 0, 0)

        # Add Fri closed → recompute remaining 120 from Thu 17:00 → Mon 10:00
        resp = await test_client.patch(
            f"/api/workspaces/{owner['workspaceId']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={
                "timezone": "Asia/Shanghai",
                "businessHours": {
                    "enabled": True,
                    "windows": _weekday_windows_mon_fri(),
                    "exceptions": [{"date": "2026-11-06", "kind": "closed"}],
                },
            },
        )
        assert resp.status_code == 200, resp.text

    after = (await _clocks(test_client, owner, issue["id"]))[0]
    assert after["deadlineAt"] != before
    assert after["status"] == "running"
    assert datetime.fromisoformat(after["deadlineAt"]) == datetime(2026, 11, 9, 2, 0, 0)


@pytest.mark.asyncio
async def test_config_write_no_extra_webhook_automation(test_client: AsyncClient):
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
                "businessHours": {
                    "enabled": True,
                    "windows": _weekday_windows_mon_fri(),
                    "exceptions": [{"date": "2026-10-01", "kind": "closed"}],
                },
            },
        )
        assert resp.status_code == 200, resp.text
        assert fw.await_count == 0
        assert fa.await_count == 0
