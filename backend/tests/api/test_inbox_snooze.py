"""E9-S3：Inbox notification snooze / unsnooze"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "snz"):
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


async def _add_member(client: AsyncClient, owner: dict, member: dict):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": "member"},
    )
    assert resp.status_code == 200, resp.text


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


async def _assigned_notification_id(client: AsyncClient, owner: dict, member: dict) -> str:
    issue = await _create_issue(client, owner, f"snz-{uuid.uuid4().hex[:6]}")
    resp = await client.put(
        f"/api/issues/{issue['id']}/assignee",
        headers=_auth(owner["token"], owner["workspaceId"]),
        params={"assignee_id": member["userId"]},
    )
    assert resp.status_code == 200, resp.text
    inbox = await client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert inbox.status_code == 200, inbox.text
    rows = [
        r
        for r in inbox.json()["data"]["rows"]
        if r["resourceId"] == issue["id"] and r["type"] == "assigned"
    ]
    assert rows, inbox.text
    return rows[0]["id"]


@pytest.mark.asyncio
async def test_snooze_hides_from_default_list(test_client: AsyncClient):
    owner = await _register(test_client, "snz_o")
    member = await _register(test_client, "snz_m")
    await _add_member(test_client, owner, member)
    nid = await _assigned_notification_id(test_client, owner, member)

    until = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
    snz = await test_client.post(
        f"/api/inbox/{nid}/snooze",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"until": until},
    )
    assert snz.status_code == 200, snz.text
    body = snz.json()["data"]
    assert body.get("snoozedUntil") or body.get("snoozed_until")

    default = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert default.status_code == 200
    ids = {r["id"] for r in default.json()["data"]["rows"]}
    assert nid not in ids

    included = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"include_snoozed": True},
    )
    assert included.status_code == 200
    rows = {r["id"]: r for r in included.json()["data"]["rows"]}
    assert nid in rows
    assert rows[nid].get("snoozedUntil") or rows[nid].get("snoozed_until")


@pytest.mark.asyncio
async def test_unsnooze_restores_to_list(test_client: AsyncClient):
    owner = await _register(test_client, "uns_o")
    member = await _register(test_client, "uns_m")
    await _add_member(test_client, owner, member)
    nid = await _assigned_notification_id(test_client, owner, member)

    until = (datetime.utcnow() + timedelta(hours=3)).isoformat() + "Z"
    assert (
        await test_client.post(
            f"/api/inbox/{nid}/snooze",
            headers=_auth(member["token"], owner["workspaceId"]),
            json={"until": until},
        )
    ).status_code == 200

    uns = await test_client.post(
        f"/api/inbox/{nid}/unsnooze",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert uns.status_code == 200, uns.text
    data = uns.json()["data"]
    assert data.get("snoozedUntil") in (None, "") or data.get("snoozed_until") in (None, "")

    default = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    ids = {r["id"] for r in default.json()["data"]["rows"]}
    assert nid in ids


@pytest.mark.asyncio
async def test_snooze_rejects_beyond_90_days(test_client: AsyncClient):
    owner = await _register(test_client, "cap_o")
    member = await _register(test_client, "cap_m")
    await _add_member(test_client, owner, member)
    nid = await _assigned_notification_id(test_client, owner, member)

    until = (datetime.utcnow() + timedelta(days=91)).isoformat() + "Z"
    resp = await test_client.post(
        f"/api/inbox/{nid}/snooze",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"until": until},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_snooze_rejects_past_until(test_client: AsyncClient):
    owner = await _register(test_client, "past_o")
    member = await _register(test_client, "past_m")
    await _add_member(test_client, owner, member)
    nid = await _assigned_notification_id(test_client, owner, member)

    until = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"
    resp = await test_client.post(
        f"/api/inbox/{nid}/snooze",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"until": until},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_snooze_other_user_404(test_client: AsyncClient):
    owner = await _register(test_client, "x_o")
    member = await _register(test_client, "x_m")
    stranger = await _register(test_client, "x_s")
    await _add_member(test_client, owner, member)
    nid = await _assigned_notification_id(test_client, owner, member)

    until = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
    resp = await test_client.post(
        f"/api/inbox/{nid}/snooze",
        headers=_auth(stranger["token"], owner["workspaceId"]),
        json={"until": until},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_expired_snooze_reappears(test_client: AsyncClient):
    """Snooze with until just ahead, then force-expire via include path + second snooze past.

    Lazy visibility: after setting until in the past through a second API that we
    cannot call (past rejected), use include_snoozed + DB-less approach:
    snooze 1s ahead, sleep 1.2s, then default list must include again.
    """
    import asyncio

    owner = await _register(test_client, "exp_o")
    member = await _register(test_client, "exp_m")
    await _add_member(test_client, owner, member)
    nid = await _assigned_notification_id(test_client, owner, member)

    until = (datetime.utcnow() + timedelta(seconds=1)).isoformat() + "Z"
    assert (
        await test_client.post(
            f"/api/inbox/{nid}/snooze",
            headers=_auth(member["token"], owner["workspaceId"]),
            json={"until": until},
        )
    ).status_code == 200

    hidden = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert nid not in {r["id"] for r in hidden.json()["data"]["rows"]}

    await asyncio.sleep(1.3)

    shown = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert nid in {r["id"] for r in shown.json()["data"]["rows"]}


@pytest.mark.asyncio
async def test_snooze_preserves_read_state(test_client: AsyncClient):
    owner = await _register(test_client, "rd_o")
    member = await _register(test_client, "rd_m")
    await _add_member(test_client, owner, member)
    nid = await _assigned_notification_id(test_client, owner, member)

    assert (
        await test_client.post(
            f"/api/inbox/{nid}/read",
            headers=_auth(member["token"], owner["workspaceId"]),
        )
    ).status_code == 200

    until = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
    assert (
        await test_client.post(
            f"/api/inbox/{nid}/snooze",
            headers=_auth(member["token"], owner["workspaceId"]),
            json={"until": until},
        )
    ).status_code == 200

    included = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
        params={"include_snoozed": True},
    )
    row = next(r for r in included.json()["data"]["rows"] if r["id"] == nid)
    assert row.get("readAt") or row.get("read_at")

    assert (
        await test_client.post(
            f"/api/inbox/{nid}/unsnooze",
            headers=_auth(member["token"], owner["workspaceId"]),
        )
    ).status_code == 200
    after = await test_client.get(
        "/api/inbox",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    row2 = next(r for r in after.json()["data"]["rows"] if r["id"] == nid)
    assert row2.get("readAt") or row2.get("read_at")
