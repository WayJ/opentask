"""E24：Insights summary 聚合 + 租户负例。"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ins"):
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


def _window(days: int = 14) -> tuple[str, str]:
    start = datetime(2026, 11, 4, 0, 0, 0)
    end = start + timedelta(days=days)
    return start.isoformat(), end.isoformat()


async def _create_cycle(client: AsyncClient, user: dict, name: str = "Sprint") -> dict:
    starts, ends = _window()
    resp = await client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "starts_at": starts, "ends_at": ends},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _activate(client: AsyncClient, user: dict, cycle_id: str) -> dict:
    resp = await client.post(
        f"/api/cycles/{cycle_id}/activate",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra) -> dict:
    body = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_insights_summary_aggregates(test_client: AsyncClient):
    user = await _register(test_client, "ins_agg")
    h = _auth(user["token"], user["workspaceId"])

    cycle = await _create_cycle(test_client, user, "Active-1")
    await _activate(test_client, user, cycle["id"])

    i1 = await _create_issue(
        test_client,
        user,
        "open-high",
        priority="high",
        assignee_id=user["userId"],
        cycle_id=cycle["id"],
        estimate_points=3,
    )
    i2 = await _create_issue(
        test_client,
        user,
        "open-unassigned",
        priority="low",
        cycle_id=cycle["id"],
        estimate_points=2,
    )
    i3 = await _create_issue(
        test_client,
        user,
        "to-resolve",
        priority="critical",
        cycle_id=cycle["id"],
        estimate_points=5,
    )
    resolved = await test_client.put(
        f"/api/issues/{i3['id']}",
        headers=h,
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200, resolved.text

    resp = await test_client.get("/api/insights/summary", headers=h)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["statusCounts"].get("open", 0) >= 2
    assert data["statusCounts"].get("resolved", 0) >= 1
    assert data["priorityCounts"].get("high", 0) >= 1
    assert data["priorityCounts"].get("low", 0) >= 1
    assert data["priorityCounts"].get("critical", 0) >= 1

    assignees = data["assigneeCounts"]
    assert any(a["assigneeId"] is None and a["count"] >= 1 for a in assignees)
    assert any(a["assigneeId"] == user["userId"] and a["count"] >= 1 for a in assignees)

    snap = data["cycleSnapshot"]
    assert snap is not None
    assert snap["cycleId"] == cycle["id"]
    assert snap["issueCount"] >= 3
    assert snap["completedCount"] >= 1
    assert float(snap["estimatePointsSum"]) >= 10.0

    trend = data["createdVsCompleted"]
    assert len(trend) == 14
    assert all("date" in d and "created" in d and "completed" in d for d in trend)
    assert sum(d["created"] for d in trend) >= 3
    assert sum(d["completed"] for d in trend) >= 1

    # explicit cycleId
    by_id = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"cycleId": cycle["id"]},
    )
    assert by_id.status_code == 200, by_id.text
    assert by_id.json()["data"]["cycleSnapshot"]["cycleId"] == cycle["id"]

    # ids used so linters don't complain in some runners
    assert i1["id"] and i2["id"]


@pytest.mark.asyncio
async def test_insights_requires_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "ins_hdr")
    resp = await test_client.get(
        "/api/insights/summary",
        headers={"Authorization": f"Bearer {user['token']}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_insights_non_member_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "ins_own")
    stranger = await _register(test_client, "ins_str")
    resp = await test_client.get(
        "/api/insights/summary",
        headers=_auth(stranger["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_insights_cross_tenant_cycle_404(test_client: AsyncClient):
    a = await _register(test_client, "ins_a")
    b = await _register(test_client, "ins_b")
    cycle = await _create_cycle(test_client, a, "A-only")
    resp = await test_client.get(
        "/api/insights/summary",
        headers=_auth(b["token"], b["workspaceId"]),
        params={"cycleId": cycle["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_insights_viewer_can_read(test_client: AsyncClient):
    owner = await _register(test_client, "ins_vo")
    viewer = await _register(test_client, "ins_vv")
    await _add_member(test_client, owner, viewer, role="viewer")
    await _create_issue(test_client, owner, "for-viewer")
    resp = await test_client.get(
        "/api/insights/summary",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "statusCounts" in data
    assert data["cycleSnapshot"] is None  # no active cycle


@pytest.mark.asyncio
async def test_insights_isolation_no_leak(test_client: AsyncClient):
    a = await _register(test_client, "ins_iso_a")
    b = await _register(test_client, "ins_iso_b")
    await _create_issue(test_client, a, "only-a", priority="critical")
    resp = await test_client.get(
        "/api/insights/summary",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # B empty workspace should not see A's critical
    assert data["priorityCounts"].get("critical", 0) == 0
    assert sum(data["statusCounts"].values()) == 0
