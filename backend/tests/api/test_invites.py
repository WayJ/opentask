"""E12-S2: workspace invites create/list/revoke/preview/accept/register."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _register(client: AsyncClient, prefix: str = "inv", invite_token: str | None = None):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    body = {"userName": uname, "password": password, "name": uname}
    if invite_token:
        body["inviteToken"] = invite_token
    resp = await client.post("/api/auth/register", json=body)
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
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_owner_creates_and_lists_invite(test_client: AsyncClient):
    owner = await _register(test_client, "inv_o")
    created = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(owner["token"]),
        json={"role": "member", "expiresInDays": 7},
    )
    assert created.status_code == 200, created.text
    data = created.json()["data"]
    assert data.get("token")
    assert data["role"] == "member"
    assert data["status"] == "pending"
    assert data.get("id") or data.get("inviteId")
    invite_id = data.get("id") or data.get("inviteId")

    listed = await test_client.get(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(owner["token"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]
    assert isinstance(rows, list)
    ids = {r.get("id") or r.get("inviteId") for r in rows}
    assert invite_id in ids
    # list must NOT echo plaintext token
    for r in rows:
        assert "token" not in r or r.get("token") in (None, "")


@pytest.mark.asyncio
async def test_member_cannot_create_invite(test_client: AsyncClient):
    owner = await _register(test_client, "inv_ow")
    member = await _register(test_client, "inv_m")
    await _add_member(test_client, owner, member, role="member")
    resp = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(member["token"]),
        json={"role": "viewer"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_preview_invite_anonymous(test_client: AsyncClient):
    owner = await _register(test_client, "inv_pv")
    created = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(owner["token"]),
        json={"role": "viewer"},
    )
    token = created.json()["data"]["token"]
    prev = await test_client.get(f"/api/invites/{token}")
    assert prev.status_code == 200, prev.text
    body = prev.json()["data"]
    assert body["role"] == "viewer"
    assert body["status"] == "pending"
    assert body.get("workspaceName")
    assert "token" not in body or body.get("token") in (None, "")


@pytest.mark.asyncio
async def test_accept_invite_and_idempotent(test_client: AsyncClient):
    owner = await _register(test_client, "inv_ac")
    guest = await _register(test_client, "inv_g")
    created = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(owner["token"]),
        json={"role": "member"},
    )
    token = created.json()["data"]["token"]
    acc = await test_client.post(
        f"/api/invites/{token}/accept",
        headers=_auth(guest["token"]),
    )
    assert acc.status_code == 200, acc.text
    members = await test_client.get(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
    )
    user_ids = {m["userId"] for m in members.json()["data"]}
    assert guest["userId"] in user_ids
    role = next(m["role"] for m in members.json()["data"] if m["userId"] == guest["userId"])
    assert role == "member"

    again = await test_client.post(
        f"/api/invites/{token}/accept",
        headers=_auth(guest["token"]),
    )
    assert again.status_code == 200, again.text


@pytest.mark.asyncio
async def test_revoke_blocks_accept(test_client: AsyncClient):
    owner = await _register(test_client, "inv_rv")
    guest = await _register(test_client, "inv_rg")
    created = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(owner["token"]),
        json={"role": "member"},
    )
    data = created.json()["data"]
    token = data["token"]
    invite_id = data.get("id") or data.get("inviteId")
    rev = await test_client.delete(
        f"/api/workspaces/{owner['workspaceId']}/invites/{invite_id}",
        headers=_auth(owner["token"]),
    )
    assert rev.status_code == 200, rev.text
    acc = await test_client.post(
        f"/api/invites/{token}/accept",
        headers=_auth(guest["token"]),
    )
    assert acc.status_code in (400, 404)


@pytest.mark.asyncio
async def test_expired_invite_cannot_accept(
    test_client: AsyncClient, test_engine: AsyncEngine
):
    owner = await _register(test_client, "inv_ex")
    guest = await _register(test_client, "inv_exg")
    created = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(owner["token"]),
        json={"role": "member"},
    )
    data = created.json()["data"]
    token = data["token"]
    invite_id = data.get("id") or data.get("inviteId")
    past = (datetime.utcnow() - timedelta(days=1)).isoformat()
    async with test_engine.begin() as conn:
        await conn.execute(
            text("UPDATE workspace_invites SET expires_at = :e WHERE id = :id"),
            {"e": past, "id": invite_id},
        )
    acc = await test_client.post(
        f"/api/invites/{token}/accept",
        headers=_auth(guest["token"]),
    )
    assert acc.status_code == 400


@pytest.mark.asyncio
async def test_register_with_invite_token(test_client: AsyncClient):
    owner = await _register(test_client, "inv_reg")
    created = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/invites",
        headers=_auth(owner["token"]),
        json={"role": "viewer"},
    )
    token = created.json()["data"]["token"]
    newbie = await _register(test_client, "inv_nb", invite_token=token)
    assert newbie["workspaceId"]  # personal default WS
    # listed in invited workspace
    members = await test_client.get(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
    )
    user_ids = {m["userId"] for m in members.json()["data"]}
    assert newbie["userId"] in user_ids
    role = next(m["role"] for m in members.json()["data"] if m["userId"] == newbie["userId"])
    assert role == "viewer"
    # personal WS still in list
    wslist = await test_client.get("/api/workspaces", headers=_auth(newbie["token"]))
    ids = {w["id"] for w in wslist.json()["data"]}
    assert newbie["workspaceId"] in ids
    assert owner["workspaceId"] in ids


@pytest.mark.asyncio
async def test_bad_token_preview_404(test_client: AsyncClient):
    resp = await test_client.get("/api/invites/not-a-real-token-xxx")
    assert resp.status_code == 404
