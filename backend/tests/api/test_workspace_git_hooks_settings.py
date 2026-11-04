"""E11-S3: Workspace gitStatusHooksEnabled settings API."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ghk"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
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
async def test_git_hooks_default_false(test_client: AsyncClient):
    user = await _register(test_client, "ghd")
    resp = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["gitStatusHooksEnabled"] is False
    assert data["gitHookOnPrOpen"] == "in_progress"
    assert data["gitHookOnPrMerged"] == "resolved"


@pytest.mark.asyncio
async def test_patch_git_hooks_enabled(test_client: AsyncClient):
    user = await _register(test_client, "ghp")
    h = _auth(user["token"], user["workspaceId"])
    patched = await test_client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=h,
        json={"gitStatusHooksEnabled": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["gitStatusHooksEnabled"] is True

    again = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}",
        headers=h,
    )
    assert again.json()["data"]["gitStatusHooksEnabled"] is True
