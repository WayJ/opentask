"""本地登录 + token 生命周期端点测试（SQLite 内存库旁路 MySQL）

覆盖（spec 3.2/8）：
1. 正常登录 → token 对 + getUserInfo 可用
2. 错密 5 次锁定，第 6 次正确密码也 401
3. 禁用用户登录 401
4. must_change_password：受限 token → 改密 → 正常 token
5. 改密校验：旧密错 401 / 新密码弱 422 / 成功后旧 access+refresh 全失效
6. refresh 轮换 + 重放全量吊销（含 /refreshToken 旧路径别名）
7. logout 吊销 refresh
8. jnpf_enabled=false 时 /login 走本地路径
9. getUserInfo 真实角色权限下发（Phase 3 Task 3）：
   admin/viewer 播种后角色与 buttons/menus 分级、jnpf_name 优先、未播种库兜底
"""
from types import SimpleNamespace
from unittest import mock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.app import App
from opentask.config import config
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import RefreshToken
from opentask.repositories.base import get_session
from opentask.services.user_center.seed import seed_user_center

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FK 解析需要：user（被引用）、refresh_token、access_tokens（user 关系引用）
# + getUserInfo 权限下发（RbacService → role/permission/role_permission/user_role）
TABLES = (
    "user",
    "refresh_token",
    "access_tokens",
    "role",
    "permission",
    "role_permission",
    "user_role",
)


@pytest_asyncio.fixture
async def flow():
    """SQLite 内存库 + dependency_overrides[get_session] 旁路 MySQL 的测试环境"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))

    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        """与 repositories.base.get_session 相同的提交/回滚语义"""
        session = maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    app = App()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield SimpleNamespace(client=client, maker=maker)

    app.dependency_overrides.clear()
    await engine.dispose()


async def _make_user(maker, username: str, password: str = "Passw0rd123", **kwargs) -> UserModel:
    """建一个带 bcrypt 哈希的本地用户（kwargs 可覆盖 status/must_change_password 等）"""
    async with maker() as session:
        user = UserModel(
            name=f"用户-{username}",
            username=username,
            password_hash=_pwd.hash(password),
            **kwargs,
        )
        session.add(user)
        await session.commit()
        # 重新查一遍，返回绑定当前 session 的干净实例
        found = (
            await session.execute(select(UserModel).where(UserModel.username == username))
        ).scalar_one()
        return found


def _login_body(username: str, password: str) -> dict:
    return {"userName": username, "password": password}


async def _all_refresh_rows(maker) -> list[RefreshToken]:
    async with maker() as session:
        return list((await session.execute(select(RefreshToken))).scalars().all())


# ============================================================================
# 1. 正常登录
# ============================================================================

async def test_login_success_and_get_user_info(flow):
    """正常登录 → 200，token+refreshToken+mustChangePassword=false；token 可访问 getUserInfo"""
    await _make_user(flow.maker, "alice", "Passw0rd123")

    resp = await flow.client.post("/api/auth/login", json=_login_body("alice", "Passw0rd123"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["token"]
    assert data["refreshToken"]
    assert data["mustChangePassword"] is False
    assert data["username"] == "alice"
    assert data["userId"]

    # access token 可访问 getUserInfo
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {data['token']}"}
    )
    assert info.status_code == 200
    assert info.json()["code"] == 200

    # 库里存的是 refresh 哈希而非明文
    rows = await _all_refresh_rows(flow.maker)
    assert len(rows) == 1
    assert rows[0].token_hash != data["refreshToken"]


# ============================================================================
# 2. 失败锁定
# ============================================================================

async def test_lockout_after_5_failures(flow):
    """错密 5 次 → 锁定，第 6 次正确密码也 401 '账户已锁定'"""
    await _make_user(flow.maker, "bob", "Passw0rd123")

    for _ in range(5):
        resp = await flow.client.post("/api/auth/login", json=_login_body("bob", "wrongpass1"))
        assert resp.status_code == 401

    # 第 6 次即使密码正确也拒绝
    resp = await flow.client.post("/api/auth/login", json=_login_body("bob", "Passw0rd123"))
    assert resp.status_code == 401
    assert "锁定" in resp.json()["detail"]

    # 未到锁定截止时间前，locked_until 已写入
    async with flow.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.username == "bob"))
        ).scalar_one()
        assert user.locked_until is not None


# ============================================================================
# 3. 禁用用户
# ============================================================================

async def test_disabled_user_login_rejected(flow):
    """status=0 的用户登录 → 401"""
    await _make_user(flow.maker, "carol", "Passw0rd123", status=0)

    resp = await flow.client.post("/api/auth/login", json=_login_body("carol", "Passw0rd123"))
    assert resp.status_code == 401
    assert "禁用" in resp.json()["detail"]


# ============================================================================
# 4. 强制改密流程
# ============================================================================

async def test_must_change_password_flow(flow):
    """must_change_password 用户：受限 token → getUserInfo 403 → 改密 → 新 token 200"""
    await _make_user(
        flow.maker, "dave", "TempPass123", must_change_password=True
    )

    resp = await flow.client.post("/api/auth/login", json=_login_body("dave", "TempPass123"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["mustChangePassword"] is True

    # 受限 token（scp=pwd_change）访问其他端点 → 403
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {data['token']}"}
    )
    assert info.status_code == 403
    assert "修改初始密码" in info.json()["detail"]

    # 受限 token 可以改密
    change = await flow.client.post(
        "/api/auth/change-password",
        json={"oldPassword": "TempPass123", "newPassword": "NewPass456"},
        headers={"Authorization": f"Bearer {data['token']}"},
    )
    assert change.status_code == 200
    new_pair = change.json()["data"]
    assert new_pair["mustChangePassword"] is False

    # 新 token 是正常 token，getUserInfo 可用
    info2 = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {new_pair['token']}"}
    )
    assert info2.status_code == 200


# ============================================================================
# 4b. 受限 token 刷新不可洗白
# ============================================================================

async def test_pwd_change_scope_survives_refresh(flow):
    """受限 refresh 轮换不能洗白：新 access 仍继承 pwd_change scope，getUserInfo 仍 403"""
    await _make_user(flow.maker, "kate", "TempPass123", must_change_password=True)

    login = await flow.client.post("/api/auth/login", json=_login_body("kate", "TempPass123"))
    pair = login.json()["data"]

    # 用受限 token 对里的 refresh 轮换
    rot = await flow.client.post(
        "/api/auth/refresh-token", json={"refreshToken": pair["refreshToken"]}
    )
    assert rot.status_code == 200
    new_pair = rot.json()["data"]
    assert new_pair["mustChangePassword"] is True

    # 轮换出的新 access 仍是受限 token，访问非改密端点 403
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {new_pair['token']}"}
    )
    assert info.status_code == 403

    # 受限 refresh 可继续走改密流程解锁
    change = await flow.client.post(
        "/api/auth/change-password",
        json={"oldPassword": "TempPass123", "newPassword": "NewPass456"},
        headers={"Authorization": f"Bearer {new_pair['token']}"},
    )
    assert change.status_code == 200
    final = change.json()["data"]
    info2 = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {final['token']}"}
    )
    assert info2.status_code == 200


# ============================================================================
# 5. 改密校验与旧凭证失效
# ============================================================================

async def test_change_password_validation_and_invalidation(flow):
    """旧密错 401；新密码弱 422；成功后旧 access（tv 已变）401，旧 refresh 全吊销"""
    await _make_user(flow.maker, "eve", "Passw0rd123")

    login = await flow.client.post("/api/auth/login", json=_login_body("eve", "Passw0rd123"))
    pair = login.json()["data"]
    headers = {"Authorization": f"Bearer {pair['token']}"}

    # 旧密错误
    resp = await flow.client.post(
        "/api/auth/change-password",
        json={"oldPassword": "WrongOld1", "newPassword": "NewPass456"},
        headers=headers,
    )
    assert resp.status_code == 401

    # 新密码弱：纯数字 / 太短
    resp = await flow.client.post(
        "/api/auth/change-password",
        json={"oldPassword": "Passw0rd123", "newPassword": "12345678"},
        headers=headers,
    )
    assert resp.status_code == 422
    resp = await flow.client.post(
        "/api/auth/change-password",
        json={"oldPassword": "Passw0rd123", "newPassword": "ab12"},
        headers=headers,
    )
    assert resp.status_code == 422

    # 改密成功
    resp = await flow.client.post(
        "/api/auth/change-password",
        json={"oldPassword": "Passw0rd123", "newPassword": "NewPass456"},
        headers=headers,
    )
    assert resp.status_code == 200
    new_pair = resp.json()["data"]
    assert new_pair["token"] and new_pair["refreshToken"]

    # 旧 access：tv 已落后 → 401 登录态已失效
    old_info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {pair['token']}"}
    )
    assert old_info.status_code == 401
    assert "登录态已失效" in old_info.json()["detail"]

    # 旧 refresh 已被全量吊销（重放触发 401）
    refresh = await flow.client.post(
        "/api/auth/refresh-token", json={"refreshToken": pair["refreshToken"]}
    )
    assert refresh.status_code == 401

    # 新 token 对可用
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {new_pair['token']}"}
    )
    assert info.status_code == 200


# ============================================================================
# 6. refresh 轮换与重放
# ============================================================================

async def test_refresh_rotation_and_replay(flow):
    """轮换得新对；旧 refresh 重放 → 401 且该用户全部 refresh 吊销"""
    await _make_user(flow.maker, "frank", "Passw0rd123")

    login = await flow.client.post("/api/auth/login", json=_login_body("frank", "Passw0rd123"))
    pair1 = login.json()["data"]

    # 新路径轮换
    rot = await flow.client.post(
        "/api/auth/refresh-token", json={"refreshToken": pair1["refreshToken"]}
    )
    assert rot.status_code == 200
    pair2 = rot.json()["data"]
    assert pair2["refreshToken"] != pair1["refreshToken"]
    assert pair2["token"]

    # 旧路径别名 /api/auth/refreshToken 也可用（前端 shared.ts 调旧路径）
    rot2 = await flow.client.post(
        "/api/auth/refreshToken", json={"refreshToken": pair2["refreshToken"]}
    )
    assert rot2.status_code == 200
    pair3 = rot2.json()["data"]

    # 重放最早的已吊销 refresh → 401
    replay = await flow.client.post(
        "/api/auth/refresh-token", json={"refreshToken": pair1["refreshToken"]}
    )
    assert replay.status_code == 401

    # 重放触发全量吊销：最新 refresh 也不可用
    dead = await flow.client.post(
        "/api/auth/refresh-token", json={"refreshToken": pair3["refreshToken"]}
    )
    assert dead.status_code == 401

    rows = await _all_refresh_rows(flow.maker)
    assert len(rows) == 3
    assert all(r.revoked_at is not None for r in rows)


# ============================================================================
# 7. logout
# ============================================================================

async def test_logout_revokes_refresh(flow):
    """logout 带 refreshToken → 吊销；无 body 也返回成功"""
    await _make_user(flow.maker, "grace", "Passw0rd123")

    login = await flow.client.post("/api/auth/login", json=_login_body("grace", "Passw0rd123"))
    pair = login.json()["data"]

    resp = await flow.client.post(
        "/api/auth/logout", json={"refreshToken": pair["refreshToken"]}
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 200

    # refresh 已不可用
    refresh = await flow.client.post(
        "/api/auth/refresh-token", json={"refreshToken": pair["refreshToken"]}
    )
    assert refresh.status_code == 401

    # 无 body 的 logout 也成功（客户端自清语义）
    bare = await flow.client.post("/api/auth/logout")
    assert bare.status_code == 200


# ============================================================================
# 8. jnpf_enabled=false 时 /login 走本地路径
# ============================================================================

async def test_login_routes_to_local_when_jnpf_disabled(flow, monkeypatch):
    """monkeypatch config.jnpf_enabled=False → /login 走本地认证而非 JNPF 转发"""
    monkeypatch.setattr(type(config), "jnpf_enabled", property(lambda self: False))
    await _make_user(flow.maker, "henry", "Passw0rd123")

    resp = await flow.client.post("/api/auth/login", json=_login_body("henry", "Passw0rd123"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["token"]
    assert data["refreshToken"]  # 本地路径同样签发 refresh
    assert data["mustChangePassword"] is False


async def test_login_local_endpoint_compatible(flow):
    """/login-local 端点保留兼容：同样返回完整 token 对"""
    await _make_user(flow.maker, "ivan", "Passw0rd123")

    resp = await flow.client.post("/api/auth/login-local", json=_login_body("ivan", "Passw0rd123"))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["token"]
    assert data["refreshToken"]
    assert data["username"] == "ivan"

    # 错密 → 401
    bad = await flow.client.post("/api/auth/login-local", json=_login_body("ivan", "nope1234"))
    assert bad.status_code == 401


# ============================================================================
# 8b. JNPF 路径：转发前服务端加密密码（J1）
# ============================================================================

async def test_jnpf_login_forwards_encrypted_password(flow, monkeypatch):
    """JNPF 登录转发 payload.password 必须是 encrypt_password(明文)，而非明文本身

    前端已改为明文提交，JNPF 平台要求密文（MD5+AES-ECB+Hex），
    加密责任收归后端（与前端旧 encrypt.ts 等价，见 tests/unit/test_encrypt.py）。
    """
    monkeypatch.setattr(type(config), "jnpf_enabled", property(lambda self: True))

    # mock JNPF 登录 + CurrentUser 两个响应
    mock_login_response = mock.Mock()
    mock_login_response.status_code = 200
    mock_login_response.json.return_value = {"code": 200, "data": {"token": "bearer jnpf_tok"}}
    mock_user_response = mock.Mock()
    mock_user_response.status_code = 200
    mock_user_response.json.return_value = {
        "code": 200,
        "data": {"userInfo": {"userId": "j1", "userName": "J1用户", "userAccount": "j1acc"}},
    }
    mock_client = mock.AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = mock.AsyncMock(return_value=None)
    mock_client.post = mock.AsyncMock(return_value=mock_login_response)
    mock_client.get = mock.AsyncMock(return_value=mock_user_response)

    with mock.patch("opentask.api.auth.router.httpx.AsyncClient", return_value=mock_client):
        resp = await flow.client.post(
            "/api/auth/login", json=_login_body("plainuser", "PlainPass123")
        )
    assert resp.status_code == 200, resp.text

    # 转发给 JNPF 的必须是服务端加密后的密文
    from opentask.utils.encrypt import encrypt_password

    forwarded = mock_client.post.call_args.kwargs["data"]
    assert forwarded["password"] == encrypt_password("PlainPass123")
    assert forwarded["password"] != "PlainPass123"
    assert forwarded["account"] == "plainuser"


# ============================================================================
# 6b. 禁用用户 refresh 轮换拒绝（J3）
# ============================================================================

async def test_rotate_refresh_rejects_disabled_user(flow):
    """用户被禁用（status=0）后，未吊销的 refresh 轮换也必须 401'用户已被禁用'"""
    await _make_user(flow.maker, "luna", "Passw0rd123")

    login = await flow.client.post("/api/auth/login", json=_login_body("luna", "Passw0rd123"))
    pair = login.json()["data"]

    # 直接改库禁用（不经过 update_user_status，单独验证 rotate_refresh 的状态校验）
    async with flow.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.username == "luna"))
        ).scalar_one()
        user.status = 0
        await session.commit()

    rot = await flow.client.post(
        "/api/auth/refresh-token", json={"refreshToken": pair["refreshToken"]}
    )
    assert rot.status_code == 401
    assert "禁用" in rot.json()["detail"]


# ============================================================================
# 9. getUserInfo 真实角色权限下发（Phase 3 Task 3）
# ============================================================================

async def _seed(flow):
    """播种权限点与系统角色（幂等）"""
    async with flow.maker() as session:
        await seed_user_center(session)


async def _login_token(flow, username: str, password: str) -> str:
    """login-local 登录并返回 access token"""
    resp = await flow.client.post(
        "/api/auth/login-local", json=_login_body(username, password)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["token"]


async def test_get_user_info_admin_permissions(flow):
    """admin（桥接 role 字符串 + 播种）：roles 真实，menus 含 manage_user，buttons 含创建用户"""
    await _seed(flow)
    await _make_user(flow.maker, "admin9", "AdminPass123", role="admin")

    token = await _login_token(flow, "admin9", "AdminPass123")
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {token}"}
    )
    assert info.status_code == 200, info.text
    data = info.json()["data"]

    assert data["roles"] == ["admin"]
    assert "manage_user" in data["menus"]  # menu:manage_user → route_key
    assert "manage:user:create" in data["buttons"]
    assert data["userId"]


async def test_get_user_info_viewer_permissions(flow):
    """viewer（桥接）：无 manage:* 按钮、无 manage_user 菜单，roles==['viewer']"""
    await _seed(flow)
    await _make_user(flow.maker, "viewer9", "ViewerPass123", role="viewer")

    token = await _login_token(flow, "viewer9", "ViewerPass123")
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {token}"}
    )
    assert info.status_code == 200, info.text
    data = info.json()["data"]

    assert data["roles"] == ["viewer"]
    assert "manage_user" not in data["menus"]
    assert not any(b.startswith("manage:") for b in data["buttons"])
    # viewer 仍有业务模块查看码（requirement:view 等）
    assert "requirement:view" in data["buttons"]


async def test_get_user_info_user_name_priority(flow):
    """userName 取值优先级：jnpf_name > name > username"""
    await _seed(flow)
    await _make_user(
        flow.maker, "zhang9", "Passw0rd123", role="admin", jnpf_name="张三丰"
    )

    token = await _login_token(flow, "zhang9", "Passw0rd123")
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {token}"}
    )
    assert info.status_code == 200, info.text
    data = info.json()["data"]

    # jnpf_name 优先于 name（"用户-zhang9"）与 username（"zhang9"）
    assert data["userName"] == "张三丰"


async def test_get_user_info_unseeded_db_fallback(flow):
    """未播种库（role/permission 表空）：roles 仍按桥接返回角色码，buttons/menus 空且不 500"""
    # 注意：此处不调 _seed
    await _make_user(flow.maker, "admin8", "AdminPass123", role="admin")

    token = await _login_token(flow, "admin8", "AdminPass123")
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {token}"}
    )
    assert info.status_code == 200, info.text
    data = info.json()["data"]

    # 角色码不依赖播种：桥接 user.role 字符串直接下发
    assert data["roles"] == ["admin"]
    # 权限集为空（播种缺失），但不 500
    assert data["buttons"] == []
    assert data["menus"] == []
