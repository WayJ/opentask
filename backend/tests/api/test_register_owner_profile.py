"""E11-S4: 注册用户 Profile/权限应对齐个人 WS owner（非纯查看者）。"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "own"):
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


@pytest.mark.asyncio
async def test_register_member_list_shows_owner(test_client: AsyncClient):
    user = await _register(test_client, "own_m")
    resp = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}/members",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 200, resp.text
    members = resp.json()["data"]
    me = next(m for m in members if m["userId"] == user["userId"])
    assert me["role"] == "owner"


@pytest.mark.asyncio
async def test_register_me_exposes_workspace_owner_and_write_perms(test_client: AsyncClient):
    user = await _register(test_client, "own_me")
    resp = await test_client.get(
        "/api/users/me",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data.get("workspaceRole") == "owner"
    # 平台角色不得再是纯 viewer（否则 Profile 只显示查看者 + *:view）
    assert data.get("role") != "viewer"
    perms = data.get("permissions") or []
    assert any(p.endswith(":create") for p in perms), perms
    assert any(p.endswith(":view") for p in perms), perms


@pytest.mark.asyncio
async def test_get_user_info_includes_workspace_role(test_client: AsyncClient):
    user = await _register(test_client, "own_gi")
    resp = await test_client.get(
        "/api/auth/getUserInfo",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data.get("workspaceRole") == "owner"
    assert "viewer" not in (data.get("roles") or []) or "developer" in (data.get("roles") or [])
