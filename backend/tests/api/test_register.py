"""开放注册 API 测试（E3-S1）"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
async def test_register_success(test_client: AsyncClient, test_session):
    uname = f"reg_{uuid.uuid4().hex[:8]}"
    resp = await test_client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": "Reg User"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["username"] == uname
    assert "token" in data
    assert "refreshToken" in data
    assert data.get("defaultWorkspaceId")

    from opentask.models.workspace.model import Workspace, WorkspaceMember

    ws_id = data["defaultWorkspaceId"]
    ws = (
        await test_session.execute(select(Workspace).where(Workspace.id == ws_id))
    ).scalar_one()
    assert ws.slug.startswith(uname.lower()) or ws.slug == uname.lower()
    member = (
        await test_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.user_id == data["userId"],
            )
        )
    ).scalar_one()
    assert member.role == "owner"


@pytest.mark.asyncio
async def test_register_duplicate_username(test_client: AsyncClient):
    uname = f"dup_{uuid.uuid4().hex[:8]}"
    payload = {"userName": uname, "password": "Passw0rd!"}
    r1 = await test_client.post("/api/auth/register", json=payload)
    assert r1.status_code == 200
    r2 = await test_client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409


CLEAR_PWD_MSG = "密码至少 8 位，且需同时包含字母和数字"


@pytest.mark.asyncio
async def test_register_weak_password(test_client: AsyncClient):
    """过短 / 缺字母或数字时返回明确中文策略文案（与 AuthService 一致）。"""
    uname = f"weak_{uuid.uuid4().hex[:8]}"

    # 过短
    resp = await test_client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "abc"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == CLEAR_PWD_MSG

    # 7 位但已含字母+数字：仍过短，文案须明示「至少 8 位」
    resp = await test_client.post(
        "/api/auth/register",
        json={"userName": f"{uname}7", "password": "Abc12x3"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == CLEAR_PWD_MSG
    assert "至少 8 位" in resp.json()["detail"]

    # 8 位纯字母
    resp = await test_client.post(
        "/api/auth/register",
        json={"userName": f"{uname}a", "password": "abcdefgh"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == CLEAR_PWD_MSG


@pytest.mark.asyncio
async def test_register_then_login_local(test_client: AsyncClient):
    uname = f"login_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    r = await test_client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password},
    )
    assert r.status_code == 200
    login = await test_client.post(
        "/api/auth/login-local",
        json={"userName": uname, "password": password},
    )
    assert login.status_code == 200
    assert login.json()["data"]["token"]
