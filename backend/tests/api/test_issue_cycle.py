"""E6-S2：Issue.cycle_id 指派 / 列表过滤 / 跨租户校验 / estimate_points"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ic"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
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


def _window(days: int = 14) -> tuple[str, str]:
    start = datetime(2026, 11, 4, 0, 0, 0)
    end = start + timedelta(days=days)
    return start.isoformat(), end.isoformat()


async def _create_cycle(client: AsyncClient, user: dict, name: str = "Cycle X") -> dict:
    starts, ends = _window()
    resp = await client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "starts_at": starts, "ends_at": ends},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra):
    body = {
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
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_create_issue_with_cycle_id(test_client: AsyncClient):
    user = await _register(test_client, "ic_c")
    cycle = await _create_cycle(test_client, user, "C1")
    issue = await _create_issue(test_client, user, "with-cycle", cycle_id=cycle["id"])
    assert issue["cycle_id"] == cycle["id"]

    got = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    assert got.json()["data"]["cycle_id"] == cycle["id"]


@pytest.mark.asyncio
async def test_update_issue_cycle_id_and_clear(test_client: AsyncClient):
    user = await _register(test_client, "ic_u")
    cycle = await _create_cycle(test_client, user, "C-upd")
    issue = await _create_issue(test_client, user, "to-assign")

    patched = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"cycle_id": cycle["id"]},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["cycle_id"] == cycle["id"]

    cleared = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"cycle_id": None},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["data"].get("cycle_id") in (None, "")


@pytest.mark.asyncio
async def test_list_issues_filter_by_cycle_id(test_client: AsyncClient):
    user = await _register(test_client, "ic_f")
    c1 = await _create_cycle(test_client, user, "F1")
    c2 = await _create_cycle(test_client, user, "F2")
    i1 = await _create_issue(test_client, user, "in-c1", cycle_id=c1["id"])
    await _create_issue(test_client, user, "in-c2", cycle_id=c2["id"])

    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"cycle_id": c1["id"], "page_size": 50},
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert len(rows) >= 1
    assert all(r["cycle_id"] == c1["id"] for r in rows)
    assert any(r["id"] == i1["id"] for r in rows)
    assert not any(r["title"] == "in-c2" for r in rows)


@pytest.mark.asyncio
async def test_list_issues_filter_none_cycle(test_client: AsyncClient):
    user = await _register(test_client, "ic_n")
    cycle = await _create_cycle(test_client, user, "N1")
    await _create_issue(test_client, user, "assigned", cycle_id=cycle["id"])
    none_issue = await _create_issue(test_client, user, "unassigned")

    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"cycle_id": "__none__", "page_size": 50},
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert any(r["id"] == none_issue["id"] for r in rows)
    assert all(r.get("cycle_id") in (None, "") for r in rows)
    assert not any(r["title"] == "assigned" for r in rows)


@pytest.mark.asyncio
async def test_reject_cross_workspace_cycle(test_client: AsyncClient):
    a = await _register(test_client, "ic_a")
    b = await _register(test_client, "ic_b")
    cycle_a = await _create_cycle(test_client, a, "A-cycle")
    issue_b = await _create_issue(test_client, b, "b-issue")

    bad = await test_client.put(
        f"/api/issues/{issue_b['id']}",
        headers=_auth(b["token"], b["workspaceId"]),
        json={"cycle_id": cycle_a["id"]},
    )
    assert bad.status_code == 400, bad.text


@pytest.mark.asyncio
async def test_create_with_estimate_points(test_client: AsyncClient):
    user = await _register(test_client, "ic_p")
    issue = await _create_issue(
        test_client,
        user,
        "points",
        estimate_points=5,
        estimated_hours=2.5,
    )
    assert float(issue["estimate_points"]) == 5.0
    assert float(issue["estimated_hours"]) == 2.5
