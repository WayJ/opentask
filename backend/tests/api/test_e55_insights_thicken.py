"""E55：Insights thicken — filters + velocity + CSV · no-emit."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e55"):
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


async def _create_project(client: AsyncClient, user: dict, name: str) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "description": name},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_tag(client: AsyncClient, user: dict, name: str) -> dict:
    resp = await client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "color": "#ef4444"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _attach_tag(client: AsyncClient, user: dict, issue_id: str, tag_id: int) -> None:
    resp = await client.post(
        f"/api/issues/{issue_id}/tags/{tag_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_summary_no_filter_regression_has_velocity(test_client: AsyncClient):
    user = await _register(test_client, "e55_reg")
    h = _auth(user["token"], user["workspaceId"])
    cycle = await _create_cycle(test_client, user, "Active-E55")
    await _activate(test_client, user, cycle["id"])
    await _create_issue(
        test_client, user, "open-a", priority="high", cycle_id=cycle["id"], estimate_points=2
    )

    resp = await test_client.get("/api/insights/summary", headers=h)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "statusCounts" in data
    assert "priorityCounts" in data
    assert "assigneeCounts" in data
    assert "cycleSnapshot" in data
    assert "createdVsCompleted" in data
    assert len(data["createdVsCompleted"]) == 14

    vel = data["estimateVelocity"]
    assert vel["windowDays"] == 14
    assert len(vel["buckets"]) == 14
    assert all("date" in b and "completedPoints" in b for b in vel["buckets"])


@pytest.mark.asyncio
async def test_summary_project_filter_narrows_counts_and_cycle(test_client: AsyncClient):
    user = await _register(test_client, "e55_proj")
    h = _auth(user["token"], user["workspaceId"])
    cycle = await _create_cycle(test_client, user, "C-proj")
    await _activate(test_client, user, cycle["id"])
    pa = await _create_project(test_client, user, "Proj-A")
    pb = await _create_project(test_client, user, "Proj-B")

    await _create_issue(
        test_client,
        user,
        "in-a",
        priority="critical",
        project_id=pa["id"],
        cycle_id=cycle["id"],
        estimate_points=3,
    )
    await _create_issue(
        test_client,
        user,
        "in-b",
        priority="low",
        project_id=pb["id"],
        cycle_id=cycle["id"],
        estimate_points=8,
    )

    full = await test_client.get("/api/insights/summary", headers=h)
    assert full.status_code == 200, full.text
    full_data = full.json()["data"]
    assert full_data["priorityCounts"].get("critical", 0) >= 1
    assert full_data["priorityCounts"].get("low", 0) >= 1
    assert float(full_data["cycleSnapshot"]["estimatePointsSum"]) >= 11.0

    filtered = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"projectId": pa["id"]},
    )
    assert filtered.status_code == 200, filtered.text
    data = filtered.json()["data"]
    assert data["priorityCounts"].get("critical", 0) >= 1
    assert data["priorityCounts"].get("low", 0) == 0
    assert sum(data["statusCounts"].values()) == 1
    snap = data["cycleSnapshot"]
    assert snap is not None
    assert snap["issueCount"] == 1
    assert float(snap["estimatePointsSum"]) == 3.0


@pytest.mark.asyncio
async def test_summary_label_filter_and_cross_tenant_404(test_client: AsyncClient):
    a = await _register(test_client, "e55_la")
    b = await _register(test_client, "e55_lb")
    ha = _auth(a["token"], a["workspaceId"])

    tag = await _create_tag(test_client, a, "bug")
    other = await _create_tag(test_client, a, "feature")
    i1 = await _create_issue(test_client, a, "bug-issue", priority="high")
    i2 = await _create_issue(test_client, a, "feat-issue", priority="low")
    await _attach_tag(test_client, a, i1["id"], tag["id"])
    await _attach_tag(test_client, a, i2["id"], other["id"])

    filtered = await test_client.get(
        "/api/insights/summary",
        headers=ha,
        params={"labelId": tag["id"]},
    )
    assert filtered.status_code == 200, filtered.text
    data = filtered.json()["data"]
    assert data["priorityCounts"].get("high", 0) >= 1
    assert data["priorityCounts"].get("low", 0) == 0
    assert sum(data["statusCounts"].values()) == 1

    # cross-tenant label → 404
    cross = await test_client.get(
        "/api/insights/summary",
        headers=_auth(b["token"], b["workspaceId"]),
        params={"labelId": tag["id"]},
    )
    assert cross.status_code == 404

    # unknown project → 404
    unknown = await test_client.get(
        "/api/insights/summary",
        headers=ha,
        params={"projectId": str(uuid.uuid4())},
    )
    assert unknown.status_code == 404


@pytest.mark.asyncio
async def test_estimate_velocity_sums_points_by_completion_day(test_client: AsyncClient):
    user = await _register(test_client, "e55_vel")
    h = _auth(user["token"], user["workspaceId"])
    i1 = await _create_issue(test_client, user, "p3", estimate_points=3)
    i2 = await _create_issue(test_client, user, "p5", estimate_points=5)
    i3 = await _create_issue(test_client, user, "no-pts")  # null estimate

    for iid in (i1["id"], i2["id"], i3["id"]):
        r = await test_client.put(
            f"/api/issues/{iid}",
            headers=h,
            json={"status": "resolved"},
        )
        assert r.status_code == 200, r.text

    resp = await test_client.get("/api/insights/summary", headers=h)
    assert resp.status_code == 200, resp.text
    buckets = resp.json()["data"]["estimateVelocity"]["buckets"]
    assert sum(float(b["completedPoints"]) for b in buckets) >= 8.0


@pytest.mark.asyncio
async def test_export_csv_matches_summary_filters(test_client: AsyncClient):
    user = await _register(test_client, "e55_csv")
    h = _auth(user["token"], user["workspaceId"])
    proj = await _create_project(test_client, user, "CSV-P")
    await _create_issue(
        test_client, user, "csv-open", priority="high", project_id=proj["id"], estimate_points=4
    )

    summary = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"projectId": proj["id"]},
    )
    assert summary.status_code == 200, summary.text

    resp = await test_client.get(
        "/api/insights/export.csv",
        headers=h,
        params={"projectId": proj["id"]},
    )
    assert resp.status_code == 200, resp.text
    ctype = resp.headers.get("content-type", "")
    assert "text/csv" in ctype
    body = resp.text
    assert "kind,key,value" in body.splitlines()[0]
    assert "status," in body
    assert "priority,high," in body
    assert "estimate_velocity," in body

    # cross-tenant project on export → 404
    other = await _register(test_client, "e55_csv_x")
    cross = await test_client.get(
        "/api/insights/export.csv",
        headers=_auth(other["token"], other["workspaceId"]),
        params={"projectId": proj["id"]},
    )
    assert cross.status_code == 404


@pytest.mark.asyncio
async def test_insights_viewer_can_read_export(test_client: AsyncClient):
    owner = await _register(test_client, "e55_vo")
    viewer = await _register(test_client, "e55_vv")
    add = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": viewer["userId"], "role": "viewer"},
    )
    assert add.status_code == 200, add.text
    await _create_issue(test_client, owner, "for-viewer")
    h = _auth(viewer["token"], owner["workspaceId"])
    s = await test_client.get("/api/insights/summary", headers=h)
    assert s.status_code == 200, s.text
    assert "estimateVelocity" in s.json()["data"]
    e = await test_client.get("/api/insights/export.csv", headers=h)
    assert e.status_code == 200, e.text


@pytest.mark.asyncio
async def test_insights_read_no_emit(test_client: AsyncClient):
    user = await _register(test_client, "e55_ne")
    h = _auth(user["token"], user["workspaceId"])
    await _create_issue(test_client, user, "ne")
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as spy:
        await test_client.get("/api/insights/summary", headers=h)
        await test_client.get("/api/insights/export.csv", headers=h)
        spy.assert_not_called()
