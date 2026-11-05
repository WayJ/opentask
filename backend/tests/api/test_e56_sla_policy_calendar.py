"""E56: SLA policy calendar overlay — API + clock wiring · no-emit."""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(test_client: AsyncClient, prefix: str = "e56", *, username: str | None = None):
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


async def _create_issue(test_client: AsyncClient, user: dict, title: str = "e56-issue", **extra) -> dict:
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
        "name": "Cal",
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


async def _enable_bh(test_client, user, *, exceptions=None, enabled=True):
    body = {
        "timezone": "Asia/Shanghai",
        "businessHours": {
            "enabled": enabled,
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
async def test_no_overlay_regression_matches_ws_calendar(test_client: AsyncClient):
    owner = await _register(test_client)
    await _enable_bh(test_client, owner, exceptions=[{"date": "2026-11-06", "kind": "closed"}])
    pol = await _create_policy(test_client, owner, targetMinutes=120)
    assert pol.get("calendar") in (None, {})
    assert "effectiveCalendar" in pol
    assert pol["effectiveCalendar"]["timezone"] == "Asia/Shanghai"
    issue = await _create_issue(test_client, owner)
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
    assert datetime.fromisoformat(rows[0]["deadlineAt"]) == datetime(2026, 11, 9, 2, 0, 0)


@pytest.mark.asyncio
async def test_policy_exceptions_override_only(test_client: AsyncClient):
    """WS has no Sat open; policy forced_open Sat → that policy counts business minutes."""
    owner = await _register(test_client)
    await _enable_bh(test_client, owner, exceptions=[])
    pol = await _create_policy(
        test_client,
        owner,
        targetMinutes=60,
        calendar={"exceptions": [{"date": "2026-11-07", "kind": "forced_open"}]},
    )
    assert pol["calendar"]["exceptions"][0]["date"] == "2026-11-07"
    assert pol["effectiveCalendar"]["exceptions"][0]["kind"] == "forced_open"
    issue = await _create_issue(test_client, owner)
    frozen = datetime(2026, 11, 7, 2, 0, 0)  # Sat 10:00 CST
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
async def test_partial_timezone_override(test_client: AsyncClient):
    owner = await _register(test_client)
    await _enable_bh(test_client, owner)
    pol = await _create_policy(
        test_client, owner, targetMinutes=60, calendar={"timezone": "UTC"}
    )
    assert pol["calendar"] == {"timezone": "UTC"}
    assert pol["effectiveCalendar"]["timezone"] == "UTC"
    assert pol["effectiveCalendar"]["windows"]["mon"]


@pytest.mark.asyncio
async def test_ws_enabled_false_wall_clock_despite_policy_calendar(test_client: AsyncClient):
    owner = await _register(test_client)
    await _enable_bh(test_client, owner, enabled=False)
    await _create_policy(
        test_client,
        owner,
        targetMinutes=60,
        calendar={
            "timezone": "Asia/Shanghai",
            "windows": _weekday_windows_mon_fri(),
            "exceptions": [{"date": "2026-11-06", "kind": "closed"}],
        },
    )
    issue = await _create_issue(test_client, owner)
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
    # wall +60m
    assert datetime.fromisoformat(rows[0]["deadlineAt"]) == datetime(2026, 11, 5, 10, 0, 0)


@pytest.mark.asyncio
async def test_policy_calendar_change_recomputes_only_that_policy(test_client: AsyncClient):
    owner = await _register(test_client)
    await _enable_bh(test_client, owner, exceptions=[])
    p1 = await _create_policy(test_client, owner, name="P1", targetMinutes=60)
    p2 = await _create_policy(test_client, owner, name="P2", targetMinutes=60)
    issue = await _create_issue(test_client, owner)
    frozen = datetime(2026, 11, 7, 2, 0, 0)  # Sat — WS sat empty → wall? No, BH enabled uses business scan
    # With empty sat window, add_business_minutes skips to Monday
    with patch("opentask.services.sla.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = frozen
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        resp = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200, resp.text
    before = {r["policyId"]: datetime.fromisoformat(r["deadlineAt"]) for r in await _clocks(test_client, owner, issue["id"])}
    assert len(before) == 2
    # Patch p1 with forced_open Sat → deadline moves earlier (Sat 11:00 UTC=03:00)
    with patch("opentask.services.sla.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = frozen
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        resp = await test_client.patch(
            f"/api/sla/policies/{p1['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"calendar": {"exceptions": [{"date": "2026-11-07", "kind": "forced_open"}]}},
        )
        assert resp.status_code == 200, resp.text
    after = {r["policyId"]: datetime.fromisoformat(r["deadlineAt"]) for r in await _clocks(test_client, owner, issue["id"])}
    assert after[p1["id"]] == datetime(2026, 11, 7, 3, 0, 0)
    assert after[p2["id"]] == before[p2["id"]]


@pytest.mark.asyncio
async def test_illegal_calendar_400_cross_tenant_404(test_client: AsyncClient):
    owner = await _register(test_client)
    other = await _register(test_client, prefix="e56o")
    pol = await _create_policy(test_client, owner)
    bad = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"calendar": {"timezone": "Not/AZone"}},
    )
    assert bad.status_code == 400
    dup = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={
            "calendar": {
                "exceptions": [
                    {"date": "2026-11-05", "kind": "closed"},
                    {"date": "2026-11-05", "kind": "forced_open"},
                ]
            }
        },
    )
    assert dup.status_code == 400
    cross = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(other["token"], other["workspaceId"]),
        json={"calendar": {"timezone": "UTC"}},
    )
    assert cross.status_code == 404
    # clear calendar
    clr = await test_client.patch(
        f"/api/sla/policies/{pol['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"calendar": None},
    )
    assert clr.status_code == 200, clr.text
    assert clr.json()["data"]["calendar"] is None


@pytest.mark.asyncio
async def test_calendar_write_no_extra_webhook_automation_formula_no_emit(test_client: AsyncClient):
    owner = await _register(test_client)
    await _enable_bh(test_client, owner)
    pol = await _create_policy(test_client, owner)
    with (
        patch("opentask.services.workspace_webhook.service.fire_webhooks", new_callable=AsyncMock) as wh,
        patch("opentask.services.automation.service.fire_automations", new_callable=AsyncMock) as auto,
    ):
        wh.return_value = None
        auto.return_value = None
        resp = await test_client.patch(
            f"/api/sla/policies/{pol['id']}",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"calendar": {"timezone": "UTC"}},
        )
        assert resp.status_code == 200, resp.text
        assert wh.await_count == 0
        assert auto.await_count == 0
