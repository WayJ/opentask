"""E6-S3：Cycle complete/rollover + capacity-hint + generate-upcoming"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "cc"):
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


async def _patch_ws(client: AsyncClient, user: dict, **fields):
    resp = await client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
        json=fields,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_cycle(
    client: AsyncClient,
    user: dict,
    *,
    name: str,
    starts: datetime,
    ends: datetime,
) -> dict:
    resp = await client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "starts_at": starts.isoformat(), "ends_at": ends.isoformat()},
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


async def _set_status(client: AsyncClient, user: dict, issue_id: str, status: str):
    resp = await client.put(
        f"/api/issues/{issue_id}/status",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": status},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_complete_into_next_rolls_incomplete(test_client: AsyncClient):
    user = await _register(test_client, "cc_in")
    await _patch_ws(test_client, user, cyclesEnabled=True, cycleRolloverPolicy="into_next")

    s1 = datetime(2026, 11, 4)
    e1 = datetime(2026, 11, 18)
    s2 = datetime(2026, 11, 18)
    e2 = datetime(2026, 12, 2)

    active = await _create_cycle(test_client, user, name="Active", starts=s1, ends=e1)
    nxt = await _create_cycle(test_client, user, name="Next", starts=s2, ends=e2)
    await _activate(test_client, user, active["id"])

    open_issue = await _create_issue(test_client, user, "open-roll", cycle_id=active["id"])
    done_issue = await _create_issue(test_client, user, "done-stay", cycle_id=active["id"])
    await _set_status(test_client, user, done_issue["id"], "resolved")

    completed = await test_client.post(
        f"/api/cycles/{active['id']}/complete",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert completed.status_code == 200, completed.text
    data = completed.json()["data"]
    assert data["cycle"]["status"] == "completed"
    assert data["cycle"]["completedAt"]
    assert data["rolledCount"] == 1
    assert data["nextCycleId"] == nxt["id"]

    open_got = await test_client.get(
        f"/api/issues/{open_issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert open_got.json()["data"]["cycle_id"] == nxt["id"]

    done_got = await test_client.get(
        f"/api/issues/{done_issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert done_got.json()["data"]["cycle_id"] == active["id"]


@pytest.mark.asyncio
async def test_complete_into_next_auto_generates_upcoming(test_client: AsyncClient):
    user = await _register(test_client, "cc_ag")
    await _patch_ws(
        test_client,
        user,
        cyclesEnabled=True,
        cycleRolloverPolicy="into_next",
        cycleDurationDays=14,
    )

    s1 = datetime(2026, 11, 4)
    e1 = datetime(2026, 11, 18)
    active = await _create_cycle(test_client, user, name="OnlyActive", starts=s1, ends=e1)
    await _activate(test_client, user, active["id"])
    open_issue = await _create_issue(test_client, user, "needs-next", cycle_id=active["id"])

    completed = await test_client.post(
        f"/api/cycles/{active['id']}/complete",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert completed.status_code == 200, completed.text
    data = completed.json()["data"]
    assert data["cycle"]["status"] == "completed"
    assert data["nextCycleId"]
    assert data["nextCycleId"] != active["id"]
    assert data["rolledCount"] == 1

    listed = await test_client.get(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "upcoming"},
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert any(r["id"] == data["nextCycleId"] for r in rows)

    open_got = await test_client.get(
        f"/api/issues/{open_issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert open_got.json()["data"]["cycle_id"] == data["nextCycleId"]


@pytest.mark.asyncio
async def test_complete_leave_unassigned(test_client: AsyncClient):
    user = await _register(test_client, "cc_lv")
    await _patch_ws(
        test_client,
        user,
        cyclesEnabled=True,
        cycleRolloverPolicy="leave_unassigned",
    )

    s1 = datetime(2026, 11, 4)
    e1 = datetime(2026, 11, 18)
    s2 = datetime(2026, 11, 18)
    e2 = datetime(2026, 12, 2)
    active = await _create_cycle(test_client, user, name="LeaveActive", starts=s1, ends=e1)
    await _create_cycle(test_client, user, name="LeaveNext", starts=s2, ends=e2)
    await _activate(test_client, user, active["id"])

    open_issue = await _create_issue(test_client, user, "clear-me", cycle_id=active["id"])
    done_issue = await _create_issue(test_client, user, "keep-me", cycle_id=active["id"])
    await _set_status(test_client, user, done_issue["id"], "closed")

    completed = await test_client.post(
        f"/api/cycles/{active['id']}/complete",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert completed.status_code == 200, completed.text
    data = completed.json()["data"]
    assert data["cycle"]["status"] == "completed"
    assert data["rolledCount"] == 1
    assert data.get("nextCycleId") in (None, "")

    open_got = await test_client.get(
        f"/api/issues/{open_issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert open_got.json()["data"].get("cycle_id") in (None, "")

    done_got = await test_client.get(
        f"/api/issues/{done_issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert done_got.json()["data"]["cycle_id"] == active["id"]


@pytest.mark.asyncio
async def test_complete_rejects_non_active(test_client: AsyncClient):
    user = await _register(test_client, "cc_na")
    await _patch_ws(test_client, user, cyclesEnabled=True)
    cyc = await _create_cycle(
        test_client,
        user,
        name="UpcomingOnly",
        starts=datetime(2026, 11, 4),
        ends=datetime(2026, 11, 18),
    )
    resp = await test_client.post(
        f"/api/cycles/{cyc['id']}/complete",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_capacity_hint_from_history_falls_back_to_issues(test_client: AsyncClient):
    """No estimate_points set → unit=issues, mean of completed counts."""
    user = await _register(test_client, "cc_ch")
    await _patch_ws(
        test_client,
        user,
        cyclesEnabled=True,
        cycleCapacityLookback=3,
        cycleRolloverPolicy="leave_unassigned",
    )

    # Build two completed cycles with 2 and 4 done issues respectively → mean 3
    for idx, done_n in enumerate((2, 4), start=1):
        starts = datetime(2026, 10, 1) + timedelta(days=14 * (idx - 1))
        ends = starts + timedelta(days=14)
        cyc = await _create_cycle(
            test_client, user, name=f"Hist{idx}", starts=starts, ends=ends
        )
        await _activate(test_client, user, cyc["id"])
        for j in range(done_n):
            issue = await _create_issue(
                test_client, user, f"h{idx}-d{j}", cycle_id=cyc["id"]
            )
            await _set_status(test_client, user, issue["id"], "resolved")
        # leftover open that will clear on leave policy
        await _create_issue(test_client, user, f"h{idx}-open", cycle_id=cyc["id"])
        done = await test_client.post(
            f"/api/cycles/{cyc['id']}/complete",
            headers=_auth(user["token"], user["workspaceId"]),
        )
        assert done.status_code == 200, done.text

    hint = await test_client.get(
        "/api/cycles/capacity-hint",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert hint.status_code == 200, hint.text
    payload = hint.json()["data"]
    assert payload["basis"] == "history"
    assert payload["unit"] == "issues"
    assert payload["lookbackN"] == 3
    assert payload["suggestedCapacity"] == 3
    assert len(payload["samples"]) == 2
    counts = sorted(s["completedIssueCount"] for s in payload["samples"])
    assert counts == [2, 4]
    assert all(float(s.get("completedPoints") or 0) == 0 for s in payload["samples"])


@pytest.mark.asyncio
async def test_capacity_hint_from_history_points(test_client: AsyncClient):
    """E16: with estimate_points, suggestedCapacity is mean of completed points."""
    user = await _register(test_client, "cc_pts")
    await _patch_ws(
        test_client,
        user,
        cyclesEnabled=True,
        cycleCapacityLookback=3,
        cycleRolloverPolicy="leave_unassigned",
    )

    # Cycle A: done points 3+5=8; Cycle B: done points 2+2+2=6 → mean 7
    for idx, points_list in enumerate(([3, 5], [2, 2, 2]), start=1):
        starts = datetime(2026, 9, 1) + timedelta(days=14 * (idx - 1))
        ends = starts + timedelta(days=14)
        cyc = await _create_cycle(
            test_client, user, name=f"Pts{idx}", starts=starts, ends=ends
        )
        await _activate(test_client, user, cyc["id"])
        for j, pts in enumerate(points_list):
            issue = await _create_issue(
                test_client,
                user,
                f"p{idx}-d{j}",
                cycle_id=cyc["id"],
                estimate_points=pts,
            )
            await _set_status(test_client, user, issue["id"], "resolved")
        done = await test_client.post(
            f"/api/cycles/{cyc['id']}/complete",
            headers=_auth(user["token"], user["workspaceId"]),
        )
        assert done.status_code == 200, done.text

    hint = await test_client.get(
        "/api/cycles/capacity-hint",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert hint.status_code == 200, hint.text
    payload = hint.json()["data"]
    assert payload["basis"] == "history"
    assert payload["unit"] == "points"
    assert payload["suggestedCapacity"] == 7
    pts = sorted(float(s["completedPoints"]) for s in payload["samples"])
    assert pts == [6.0, 8.0]


@pytest.mark.asyncio
async def test_capacity_hint_members_fallback(test_client: AsyncClient):
    owner = await _register(test_client, "cc_cm")
    m1 = await _register(test_client, "cc_m1")
    await _add_member(test_client, owner, m1, role="member")
    await _patch_ws(test_client, owner, cyclesEnabled=True, cycleCapacityLookback=3)

    hint = await test_client.get(
        "/api/cycles/capacity-hint",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert hint.status_code == 200, hint.text
    payload = hint.json()["data"]
    assert payload["basis"] == "members"
    assert payload["unit"] == "members"
    assert payload["suggestedCapacity"] == 2  # owner + member
    assert payload["samples"] == []


@pytest.mark.asyncio
async def test_generate_upcoming(test_client: AsyncClient):
    user = await _register(test_client, "cc_gu")
    await _patch_ws(test_client, user, cyclesEnabled=True, cycleDurationDays=14)
    first = await _create_cycle(
        test_client,
        user,
        name="Seed",
        starts=datetime(2026, 11, 4),
        ends=datetime(2026, 11, 18),
    )

    gen = await test_client.post(
        "/api/cycles/generate-upcoming",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert gen.status_code == 200, gen.text
    data = gen.json()["data"]
    assert data["status"] == "upcoming"
    assert data["id"] != first["id"]
    # starts at/after previous ends
    assert "2026-11-18" in str(data["startsAt"]) or data["startsAt"] >= first["endsAt"]


@pytest.mark.asyncio
async def test_viewer_cannot_complete_or_generate(test_client: AsyncClient):
    owner = await _register(test_client, "cc_vo")
    viewer = await _register(test_client, "cc_vv")
    await _add_member(test_client, owner, viewer, role="viewer")
    await _patch_ws(test_client, owner, cyclesEnabled=True)

    cyc = await _create_cycle(
        test_client,
        owner,
        name="V-Active",
        starts=datetime(2026, 11, 4),
        ends=datetime(2026, 11, 18),
    )
    await _activate(test_client, owner, cyc["id"])

    complete = await test_client.post(
        f"/api/cycles/{cyc['id']}/complete",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert complete.status_code == 403, complete.text

    gen = await test_client.post(
        "/api/cycles/generate-upcoming",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert gen.status_code == 403, gen.text
