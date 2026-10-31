"""钉钉免密登录端点测试（Phase 4 Task 3，SQLite 内存库 + Fake 客户端，无真实钉钉凭据）

覆盖：
1. 已绑定用户（dingtalk_user_id 命中）→ callback → token 对，token 可访问 getUserInfo
2. 新用户 + 自动建号开关 true → 建号（role=viewer/username 唯一化/部门映射）→ token 可用
3. 新用户 + 开关 false → 403 未开通账号
4. 已绑定但禁用用户 → 403 用户已被禁用
5. 凭据未配置 → 400
6. 钉钉 detail 无部门 → 建号成功且无 user_dept 行
"""
from types import SimpleNamespace

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.api.auth import router as auth_router
from opentask.app import App
from opentask.config import config
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, UserDept
from opentask.repositories.base import get_session

# 登录链路（user/refresh_token/access_tokens）+ getUserInfo 权限下发
# （role/permission/role_permission/user_role）+ 部门归属（department/user_dept）
TABLES = (
    "user",
    "refresh_token",
    "access_tokens",
    "role",
    "permission",
    "role_permission",
    "user_role",
    "department",
    "user_dept",
)


class FakeDingTalkClient:
    """免登链路假客户端：authCode → userid → 固定 detail（接口与 DingTalkClient 一致）"""

    def __init__(self, code_map: dict[str, str], users: dict[str, dict]):
        self.code_map = code_map  # auth_code -> userid
        self.users = users  # userid -> detail（不含 userid 键）

    async def get_userid_by_code(self, auth_code: str) -> str:
        userid = self.code_map.get(auth_code)
        if not userid:
            from opentask.services.user_center.dingtalk.client import DingTalkError

            raise DingTalkError("钉钉免登失败: 响应缺少 userid")
        return userid

    async def get_user_detail(self, userid: str) -> dict:
        return {"userid": userid, **self.users[userid]}


@pytest_asyncio.fixture
async def flow(monkeypatch):
    """SQLite 内存库 + get_session 覆盖 + 凭据置空的测试环境。

    dingtalk 凭据默认置空（400 分支可直接触发）；需要真实链路的测试
    monkeypatch auth_router._build_dingtalk_client 注入 FakeDingTalkClient。
    """
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))

    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
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

    monkeypatch.setattr(type(config), "dingtalk_app_key", property(lambda self: ""))
    monkeypatch.setattr(type(config), "dingtalk_app_secret", property(lambda self: ""))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield SimpleNamespace(client=client, maker=maker, monkeypatch=monkeypatch)

    app.dependency_overrides.clear()
    await engine.dispose()


def _inject_fake(flow, fake: FakeDingTalkClient) -> None:
    """把 Fake 客户端注入路由（绕过凭据检查与真实 HTTP）"""
    flow.monkeypatch.setattr(auth_router, "_build_dingtalk_client", lambda: fake)


async def _callback(flow, auth_code: str = "code-1"):
    return await flow.client.post("/api/auth/dingtalk/callback", json={"authCode": auth_code})


async def _make_dept(maker, name: str, dt_id: str, path: str) -> Department:
    async with maker() as session:
        dept = Department(name=name, dingtalk_dept_id=dt_id, path=path, sort=1)
        session.add(dept)
        await session.commit()
        found = (
            await session.execute(
                select(Department).where(Department.dingtalk_dept_id == dt_id)
            )
        ).scalar_one()
        return found


async def _user_by_dt(maker, userid: str) -> UserModel:
    async with maker() as session:
        return (
            await session.execute(
                select(UserModel).where(UserModel.dingtalk_user_id == userid)
            )
        ).scalar_one()


async def _user_depts(maker, user_id: str) -> dict[str, bool]:
    async with maker() as session:
        rows = (
            await session.execute(select(UserDept).where(UserDept.user_id == user_id))
        ).scalars().all()
        return {r.dept_id: bool(r.is_primary) for r in rows}


# ============================================================================
# 1. 已绑定用户
# ============================================================================


async def test_bound_user_login_success(flow):
    """已绑定用户 callback → 200 token 对；access 可访问 getUserInfo"""
    async with flow.maker() as session:
        session.add(
            UserModel(
                name="张三",
                username="zhangsan",
                role="viewer",
                dingtalk_user_id="u1",
            )
        )
        await session.commit()

    fake = FakeDingTalkClient(
        {"code-1": "u1"},
        {"u1": {"name": "张三", "dept_id_list": [10], "main_dept_id": 10}},
    )
    _inject_fake(flow, fake)

    resp = await _callback(flow)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["token"]
    assert data["refreshToken"]
    assert data["mustChangePassword"] is False
    assert data["username"] == "zhangsan"

    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {data['token']}"}
    )
    assert info.status_code == 200, info.text
    assert info.json()["code"] == 200


# ============================================================================
# 2. 新用户 + 自动建号
# ============================================================================


async def test_auto_register_new_user(flow):
    """新用户开关 true → 建号：role=viewer、username 唯一化、部门映射正确、token 可用"""
    # 存量同名用户 → 钉钉"张三"应被唯一化为 张三_2
    async with flow.maker() as session:
        session.add(UserModel(name="张三", username="张三", role="viewer"))
        await session.commit()
    rd = await _make_dept(flow.maker, "研发部", "10", "/1")
    fe = await _make_dept(flow.maker, "前端组", "11", "/1/2")

    fake = FakeDingTalkClient(
        {"code-1": "u9"},
        {"u9": {"name": "张三", "dept_id_list": [10, 11], "main_dept_id": 11}},
    )
    _inject_fake(flow, fake)

    resp = await _callback(flow)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["token"] and data["refreshToken"]

    # DB 断言：建号字段
    user = await _user_by_dt(flow.maker, "u9")
    assert user.role == "viewer"
    assert user.status == 1
    assert user.password_hash is None
    assert user.name == "张三"
    assert user.jnpf_name == "张三"
    assert user.username == "张三_2"

    # 部门映射：10/11 都挂上，主部门 = main_dept_id(11)
    assert await _user_depts(flow.maker, str(user.id)) == {
        str(rd.id): False,
        str(fe.id): True,
    }

    # 返回的 userId 与库一致，token 可访问 getUserInfo
    assert data["userId"] == str(user.id)
    info = await flow.client.get(
        "/api/auth/getUserInfo", headers={"Authorization": f"Bearer {data['token']}"}
    )
    assert info.status_code == 200, info.text
    assert info.json()["data"]["roles"] == ["viewer"]  # 未播种库桥接兜底


# ============================================================================
# 3. 新用户 + 开关关闭
# ============================================================================


async def test_auto_register_disabled_403(flow):
    """开关 false 且用户不存在 → 403 未开通账号，不建号"""
    flow.monkeypatch.setattr(
        type(config), "dingtalk_auto_register", property(lambda self: False)
    )
    fake = FakeDingTalkClient(
        {"code-1": "u8"}, {"u8": {"name": "王五", "dept_id_list": [10]}}
    )
    _inject_fake(flow, fake)

    resp = await _callback(flow)
    assert resp.status_code == 403
    assert "未开通账号" in resp.json()["detail"]

    async with flow.maker() as session:
        users = (await session.execute(select(UserModel))).scalars().all()
    assert users == []  # 未建号


# ============================================================================
# 4. 已绑定但禁用
# ============================================================================


async def test_disabled_bound_user_403(flow):
    """status=0 的已绑定用户 → 403 用户已被禁用"""
    async with flow.maker() as session:
        session.add(
            UserModel(
                name="李四",
                username="lisi",
                role="viewer",
                status=0,
                dingtalk_user_id="u2",
            )
        )
        await session.commit()

    fake = FakeDingTalkClient(
        {"code-1": "u2"}, {"u2": {"name": "李四", "dept_id_list": [10]}}
    )
    _inject_fake(flow, fake)

    resp = await _callback(flow)
    assert resp.status_code == 403
    assert "用户已被禁用" in resp.json()["detail"]


# ============================================================================
# 5. 凭据未配置 → 400
# ============================================================================


async def test_callback_400_without_credentials(flow):
    """钉钉凭据为空（fixture 已置空，不注入 fake）→ 400 未配置钉钉应用凭据"""
    resp = await _callback(flow)
    assert resp.status_code == 400
    assert "未配置钉钉应用凭据" in resp.json()["detail"]


# ============================================================================
# 6. 钉钉 detail 无部门
# ============================================================================


async def test_auto_register_without_depts(flow):
    """detail 无 dept_id_list → 建号成功且无 user_dept 行"""
    await _make_dept(flow.maker, "研发部", "10", "/1")  # 本地有部门但钉钉侧无归属
    fake = FakeDingTalkClient(
        {"code-1": "u7"}, {"u7": {"name": "赵六", "dept_id_list": []}}
    )
    _inject_fake(flow, fake)

    resp = await _callback(flow)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["token"]

    user = await _user_by_dt(flow.maker, "u7")
    assert user.username == "赵六"
    assert await _user_depts(flow.maker, str(user.id)) == {}
