"""E6-S1：Workspace Cycles CRUD + 设置列 + 租户隔离"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "cy"):
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


@pytest.mark.asyncio
async def test_create_and_list_cycles(test_client: AsyncClient):
    user = await _register(test_client, "cy_c")
    starts, ends = _window()
    create = await test_client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "Cycle 1", "starts_at": starts, "ends_at": ends},
    )
    assert create.status_code == 200, create.text
    body = create.json()["data"]
    assert body["name"] == "Cycle 1"
    assert body["status"] == "upcoming"
    assert body["workspaceId"] == user["workspaceId"]
    assert body["startsAt"]
    assert body["endsAt"]
    cycle_id = body["id"]

    listed = await test_client.get(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert any(r["id"] == cycle_id for r in rows)

    one = await test_client.get(
        f"/api/cycles/{cycle_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.status_code == 200, one.text
    assert one.json()["data"]["id"] == cycle_id


@pytest.mark.asyncio
async def test_cycles_cross_workspace_isolation(test_client: AsyncClient):
    a = await _register(test_client, "cy_a")
    b = await _register(test_client, "cy_b")
    starts, ends = _window()
    created = await test_client.post(
        "/api/cycles",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "A-only", "starts_at": starts, "ends_at": ends},
    )
    assert created.status_code == 200, created.text
    cycle_id = created.json()["data"]["id"]

    forbidden_list = await test_client.get(
        "/api/cycles",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert forbidden_list.status_code == 403

    # B uses own workspace header → must not see A's cycle
    b_list = await test_client.get(
        "/api/cycles",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert b_list.status_code == 200, b_list.text
    b_ids = {r["id"] for r in b_list.json()["data"]["rows"]}
    assert cycle_id not in b_ids

    b_get = await test_client.get(
        f"/api/cycles/{cycle_id}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert b_get.status_code == 404


@pytest.mark.asyncio
async def test_delete_upcoming_cycle(test_client: AsyncClient):
    user = await _register(test_client, "cy_d")
    starts, ends = _window()
    created = await test_client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "to-delete", "starts_at": starts, "ends_at": ends},
    )
    cycle_id = created.json()["data"]["id"]

    deleted = await test_client.delete(
        f"/api/cycles/{cycle_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    listed = await test_client.get(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    ids = {r["id"] for r in listed.json()["data"]["rows"]}
    assert cycle_id not in ids

    gone = await test_client.get(
        f"/api/cycles/{cycle_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_refuse_delete_active_cycle(test_client: AsyncClient):
    user = await _register(test_client, "cy_ad")
    starts, ends = _window()
    created = await test_client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "active-soon", "starts_at": starts, "ends_at": ends},
    )
    cycle_id = created.json()["data"]["id"]

    activated = await test_client.post(
        f"/api/cycles/{cycle_id}/activate",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["data"]["status"] == "active"

    deleted = await test_client.delete(
        f"/api/cycles/{cycle_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code in (400, 409), deleted.text


@pytest.mark.asyncio
async def test_activate_enforces_single_active(test_client: AsyncClient):
    user = await _register(test_client, "cy_sa")
    s1, e1 = _window(14)
    s2, e2 = _window(28)
    # shift second window forward
    s2 = (datetime(2026, 11, 18)).isoformat()
    e2 = (datetime(2026, 12, 2)).isoformat()

    c1 = await test_client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "C1", "starts_at": s1, "ends_at": e1},
    )
    c2 = await test_client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "C2", "starts_at": s2, "ends_at": e2},
    )
    id1 = c1.json()["data"]["id"]
    id2 = c2.json()["data"]["id"]

    a1 = await test_client.post(
        f"/api/cycles/{id1}/activate",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert a1.status_code == 200, a1.text

    a2 = await test_client.post(
        f"/api/cycles/{id2}/activate",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert a2.status_code == 400, a2.text


@pytest.mark.asyncio
async def test_update_cycle_name_and_dates(test_client: AsyncClient):
    user = await _register(test_client, "cy_u")
    starts, ends = _window()
    created = await test_client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "tmp", "starts_at": starts, "ends_at": ends},
    )
    cycle_id = created.json()["data"]["id"]
    new_end = (datetime(2026, 11, 20)).isoformat()

    patched = await test_client.patch(
        f"/api/cycles/{cycle_id}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "Renamed", "ends_at": new_end},
    )
    assert patched.status_code == 200, patched.text
    data = patched.json()["data"]
    assert data["name"] == "Renamed"
    assert "2026-11-20" in str(data["endsAt"])


@pytest.mark.asyncio
async def test_cycles_require_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "cy_h")
    missing = await test_client.get("/api/cycles", headers=_auth(user["token"]))
    assert missing.status_code == 400

    other = await _register(test_client, "cy_o")
    forbidden = await test_client.get(
        "/api/cycles",
        headers=_auth(user["token"], other["workspaceId"]),
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_cycle(test_client: AsyncClient):
    owner = await _register(test_client, "cy_vo")
    viewer = await _register(test_client, "cy_vv")
    await _add_member(test_client, owner, viewer, role="viewer")
    starts, ends = _window()
    create = await test_client.post(
        "/api/cycles",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"name": "nope", "starts_at": starts, "ends_at": ends},
    )
    assert create.status_code == 403, create.text


@pytest.mark.asyncio
async def test_owner_patch_cycles_enabled(test_client: AsyncClient):
    user = await _register(test_client, "cy_en")
    patched = await test_client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
        json={
            "cyclesEnabled": True,
            "cycleDurationDays": 21,
            "cycleRolloverPolicy": "leave_unassigned",
            "cycleCapacityLookback": 5,
        },
    )
    assert patched.status_code == 200, patched.text
    data = patched.json()["data"]
    assert data["cyclesEnabled"] is True
    assert data["cycleDurationDays"] == 21
    assert data["cycleRolloverPolicy"] == "leave_unassigned"
    assert data["cycleCapacityLookback"] == 5

    got = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
    )
    assert got.status_code == 200, got.text
    again = got.json()["data"]
    assert again["cyclesEnabled"] is True
    assert again["cycleDurationDays"] == 21


@pytest.mark.asyncio
async def test_member_cannot_patch_cycle_settings(test_client: AsyncClient):
    owner = await _register(test_client, "cy_mo")
    member = await _register(test_client, "cy_mm")
    await _add_member(test_client, owner, member, role="member")
    patched = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}",
        headers=_auth(member["token"]),
        json={"cyclesEnabled": True},
    )
    assert patched.status_code == 403, patched.text


@pytest.mark.asyncio
async def test_create_rejects_ends_before_starts(test_client: AsyncClient):
    user = await _register(test_client, "cy_bad")
    create = await test_client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": "bad",
            "starts_at": "2026-11-18T00:00:00",
            "ends_at": "2026-11-04T00:00:00",
        },
    )
    assert create.status_code == 400, create.text
