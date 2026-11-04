"""E12-S2: PATCH member role + leave + add_member 409 preserved."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ms"):
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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _add_member(client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_owner_patches_member_role(test_client: AsyncClient):
    owner = await _register(test_client, "ms_o")
    member = await _register(test_client, "ms_m")
    await _add_member(test_client, owner, member, role="member")
    resp = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}/members/{member['userId']}",
        headers=_auth(owner["token"]),
        json={"role": "viewer"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["role"] == "viewer"


@pytest.mark.asyncio
async def test_cannot_demote_last_owner(test_client: AsyncClient):
    owner = await _register(test_client, "ms_lo")
    resp = await test_client.patch(
        f"/api/workspaces/{owner['workspaceId']}/members/{owner['userId']}",
        headers=_auth(owner["token"]),
        json={"role": "member"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_member_can_leave(test_client: AsyncClient):
    owner = await _register(test_client, "ms_lv")
    member = await _register(test_client, "ms_lvm")
    await _add_member(test_client, owner, member, role="member")
    leave = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/leave",
        headers=_auth(member["token"]),
    )
    assert leave.status_code == 200, leave.text
    members = await test_client.get(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
    )
    ids = {m["userId"] for m in members.json()["data"]}
    assert member["userId"] not in ids


@pytest.mark.asyncio
async def test_sole_owner_cannot_leave(test_client: AsyncClient):
    owner = await _register(test_client, "ms_so")
    leave = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/leave",
        headers=_auth(owner["token"]),
    )
    assert leave.status_code == 400


@pytest.mark.asyncio
async def test_add_member_duplicate_still_409(test_client: AsyncClient):
    owner = await _register(test_client, "ms_dup")
    member = await _register(test_client, "ms_dupm")
    await _add_member(test_client, owner, member, role="member")
    again = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": "member"},
    )
    assert again.status_code == 409
