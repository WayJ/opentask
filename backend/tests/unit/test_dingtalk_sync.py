"""钉钉通讯录全量同步对账测试（Phase 4 Task 2，全 mock，无真实钉钉凭据）

覆盖：
1. 首轮全建：3 部门 2 层 + 3 用户 → diff 计数、path、user_dept 归属正确
2. 二轮幂等：同数据 → created=0 / updated=0 / disabled=0
3. 钉钉删 1 人 → 本地 status=0 + refresh token 全吊销
4. 钉钉删 1 部门 → 本地部门 status=0
5. 用户调部门 → user_dept 跟随（覆盖式）
6. username 撞库 → 唯一化（新用户 name 与存量重复）
7. 凭据未配置 → POST /api/dingtalk/sync 400；DingTalkClient 构造即抛
"""
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.app import App
from opentask.config import config
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, RefreshToken, UserDept
from opentask.repositories.base import get_session
from opentask.services.user_center.dingtalk.client import DingTalkClient, DingTalkError
from opentask.services.user_center.dingtalk.sync_service import DingTalkSyncService
from opentask.services.user_center.seed import seed_user_center

# 同步对账涉及的表
TABLES = ("user", "department", "user_dept", "refresh_token")

# 登录链路 + 权限门槛（require_permission → RbacService）所需表（400 端点测试用）
API_TABLES = TABLES + ("access_tokens", "role", "permission", "role_permission", "user_role")


# ============================================================================
# Fake 钉钉客户端：snapshot 固定结构，测试间直接改 dict 模拟钉钉侧变化
# ============================================================================


class FakeDingTalkClient:
    """按 snapshot 返回固定结构的假客户端（接口与 DingTalkClient 一致）"""

    def __init__(self, snapshot: dict):
        self.snapshot = snapshot

    async def list_sub_depts(self, parent_id: int) -> list[dict]:
        return [d for d in self.snapshot["depts"] if d["parent_id"] == parent_id]

    async def list_dept_users(self, dept_id: int) -> list[dict]:
        return [
            {"userid": uid, "name": self.snapshot["users"][uid]["name"]}
            for uid in self.snapshot["dept_users"].get(dept_id, [])
        ]

    async def get_user_detail(self, userid: str) -> dict:
        return {"userid": userid, **self.snapshot["users"][userid]}


def base_snapshot() -> dict:
    """钉钉侧通讯录快照：2 层 3 部门（研发部>前端组、市场部）+ 3 用户"""
    return {
        "depts": [
            {"dept_id": 10, "name": "研发部", "parent_id": 1, "order": 1},
            {"dept_id": 11, "name": "前端组", "parent_id": 10, "order": 1},
            {"dept_id": 20, "name": "市场部", "parent_id": 1, "order": 2},
        ],
        "dept_users": {1: [], 10: ["u1", "u2", "u3"], 11: ["u2"], 20: ["u3"]},
        "users": {
            "u1": {"name": "张三", "dept_id_list": [10], "main_dept_id": 10},
            "u2": {"name": "李四", "dept_id_list": [10, 11], "main_dept_id": 11},
            "u3": {"name": "王五", "dept_id_list": [10, 20], "main_dept_id": 20},
        },
    }


# ============================================================================
# fixtures
# ============================================================================


@pytest_asyncio.fixture
async def session_maker():
    """SQLite 内存库会话工厂（service 级测试）"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest_asyncio.fixture
async def api_env(monkeypatch):
    """app 级测试环境：内存库 + get_session 覆盖 + 未配置钉钉凭据"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in API_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as session:
        await seed_user_center(session)

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

    # 强制钉钉凭据为空（默认即空，显式设置防本地 .env 泄漏影响测试）
    monkeypatch.setattr(type(config), "dingtalk_app_key", property(lambda self: ""))
    monkeypatch.setattr(type(config), "dingtalk_app_secret", property(lambda self: ""))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield SimpleNamespaceLike(client=client, maker=maker)

    app.dependency_overrides.clear()
    await engine.dispose()


class SimpleNamespaceLike:
    def __init__(self, **kw):
        self.__dict__.update(kw)


async def _sync(maker, snapshot: dict) -> dict:
    """用 snapshot 的 fake client 跑一次全量同步"""
    async with maker() as session:
        result = await DingTalkSyncService(session, FakeDingTalkClient(snapshot)).sync_all()
    return result


async def _dept_by_dt(maker, dt_id: str) -> Department:
    async with maker() as session:
        return (
            await session.execute(
                select(Department).where(Department.dingtalk_dept_id == dt_id)
            )
        ).scalar_one()


async def _user_by_dt(maker, userid: str) -> UserModel:
    async with maker() as session:
        return (
            await session.execute(
                select(UserModel).where(UserModel.dingtalk_user_id == userid)
            )
        ).scalar_one()


async def _user_depts(maker, user_id: str) -> dict[str, bool]:
    """user_dept 行：dept_id -> is_primary"""
    async with maker() as session:
        rows = (
            await session.execute(select(UserDept).where(UserDept.user_id == user_id))
        ).scalars().all()
        return {r.dept_id: bool(r.is_primary) for r in rows}


# ============================================================================
# 1. 首轮全建
# ============================================================================


async def test_first_sync_full_creation(session_maker):
    """3 部门 2 层 + 3 用户全建：diff 计数、path、user_dept 归属正确"""
    diff = await _sync(session_maker, base_snapshot())

    assert diff == {
        "depts": {"created": 3, "updated": 0, "disabled": 0},
        "users": {"created": 3, "updated": 0, "disabled": 0},
    }

    rd = await _dept_by_dt(session_maker, "10")
    fe = await _dept_by_dt(session_maker, "11")
    mk = await _dept_by_dt(session_maker, "20")
    # path 按 dept_service 同款算法：根 f"/{id}"，子级逐层拼接
    assert rd.path == f"/{rd.id}" and rd.parent_id is None
    assert fe.path == f"/{rd.id}/{fe.id}" and str(fe.parent_id) == str(rd.id)
    assert mk.path == f"/{mk.id}" and mk.parent_id is None

    # 用户：role=viewer、无密码、username=钉钉姓名、sso_name 写入
    u1 = await _user_by_dt(session_maker, "u1")
    u2 = await _user_by_dt(session_maker, "u2")
    u3 = await _user_by_dt(session_maker, "u3")
    for u in (u1, u2, u3):
        assert u.role == "viewer"
        assert u.password_hash is None
        assert u.status == 1
    assert u1.username == "张三" and u1.sso_name == "张三"
    assert u2.username == "李四"

    # user_dept 归属：以 detail 的 dept_id_list 为准，主部门取 main_dept_id
    assert await _user_depts(session_maker, str(u1.id)) == {str(rd.id): True}
    assert await _user_depts(session_maker, str(u2.id)) == {
        str(rd.id): False,
        str(fe.id): True,  # main_dept_id=11 → 前端组为主部门
    }
    assert await _user_depts(session_maker, str(u3.id)) == {
        str(rd.id): False,
        str(mk.id): True,
    }


# ============================================================================
# 2. 二轮幂等
# ============================================================================


async def test_second_sync_idempotent(session_maker):
    """同数据重跑：created=0，无实质变化（updated=0，disabled=0）"""
    snapshot = base_snapshot()
    first = await _sync(session_maker, snapshot)
    assert first["depts"]["created"] == 3 and first["users"]["created"] == 3

    second = await _sync(session_maker, snapshot)
    assert second == {
        "depts": {"created": 0, "updated": 0, "disabled": 0},
        "users": {"created": 0, "updated": 0, "disabled": 0},
    }


# ============================================================================
# 3. 钉钉删人 → 禁用 + 吊销全部 refresh token
# ============================================================================


async def test_removed_user_disabled_and_tokens_revoked(session_maker):
    """钉钉删 u1 → 本地 u1 status=0 + refresh token 全吊销；其余用户不动"""
    snapshot = base_snapshot()
    await _sync(session_maker, snapshot)
    u1 = await _user_by_dt(session_maker, "u1")
    u2 = await _user_by_dt(session_maker, "u2")

    # 给 u1 / u2 各造 2 个有效 refresh token（库存哈希）
    async with session_maker() as session:
        for uid in (str(u1.id), str(u2.id)):
            for i in range(2):
                session.add(
                    RefreshToken(
                        user_id=uid,
                        token_hash=f"{uid[:4]}{'a' * 59}{i}",  # 64 位定长且互不重复
                        expires_at=datetime.utcnow() + timedelta(days=7),
                    )
                )
        await session.commit()

    # 钉钉侧删除 u1
    snapshot["dept_users"][10] = ["u2", "u3"]
    del snapshot["users"]["u1"]

    diff = await _sync(session_maker, snapshot)
    assert diff["users"] == {"created": 0, "updated": 0, "disabled": 1}

    u1 = await _user_by_dt(session_maker, "u1")
    assert u1.status == 0

    async with session_maker() as session:
        tokens = (
            await session.execute(select(RefreshToken))
        ).scalars().all()
    u1_tokens = [t for t in tokens if t.user_id == str(u1.id)]
    u2_tokens = [
        t for t in tokens if t.user_id == str(u2.id)
    ]
    assert len(u1_tokens) == 2
    assert all(t.revoked_at is not None for t in u1_tokens)  # 全吊销
    assert all(t.revoked_at is None for t in u2_tokens)  # 在职用户不受影响
    assert (await _user_by_dt(session_maker, "u2")).status == 1


# ============================================================================
# 4. 钉钉删部门 → 本地禁用
# ============================================================================


async def test_removed_dept_disabled(session_maker):
    """钉钉删市场部(20) → 本地该部门 status=0；研发部/前端组不动"""
    snapshot = base_snapshot()
    await _sync(session_maker, snapshot)

    snapshot["depts"] = [d for d in snapshot["depts"] if d["dept_id"] != 20]
    snapshot["dept_users"].pop(20)
    snapshot["users"]["u3"]["dept_id_list"] = [10]
    snapshot["users"]["u3"]["main_dept_id"] = 10

    diff = await _sync(session_maker, snapshot)
    assert diff["depts"] == {"created": 0, "updated": 0, "disabled": 1}

    mk = await _dept_by_dt(session_maker, "20")
    assert mk.status == 0
    assert (await _dept_by_dt(session_maker, "10")).status == 1
    assert (await _dept_by_dt(session_maker, "11")).status == 1


# ============================================================================
# 5. 用户调部门 → user_dept 覆盖式跟随
# ============================================================================


async def test_user_dept_move_follows_dingtalk(session_maker):
    """u2 调岗：dept_id_list=[10]、主部门改 10 → user_dept 只剩研发部且为主"""
    snapshot = base_snapshot()
    await _sync(session_maker, snapshot)
    u2 = await _user_by_dt(session_maker, "u2")
    rd = await _dept_by_dt(session_maker, "10")
    fe = await _dept_by_dt(session_maker, "11")

    before = await _user_depts(session_maker, str(u2.id))
    assert before == {str(rd.id): False, str(fe.id): True}

    snapshot["dept_users"] = {1: [], 10: ["u1", "u2", "u3"], 11: [], 20: ["u3"]}
    snapshot["users"]["u2"]["dept_id_list"] = [10]
    snapshot["users"]["u2"]["main_dept_id"] = 10

    diff = await _sync(session_maker, snapshot)
    assert diff["users"]["updated"] == 1
    assert await _user_depts(session_maker, str(u2.id)) == {str(rd.id): True}


# ============================================================================
# 6. username 撞库 → 唯一化
# ============================================================================


async def test_username_collision_uniquified(session_maker):
    """存量用户已叫"张三" → 钉钉新建张三得到 username=张三_2（lower 归一化判重）"""
    snapshot = base_snapshot()
    async with session_maker() as session:
        session.add(UserModel(name="张三", username="张三", role="viewer"))
        await session.commit()

    diff = await _sync(session_maker, snapshot)
    assert diff["users"]["created"] == 3

    dingtalk_zhangsan = await _user_by_dt(session_maker, "u1")
    assert dingtalk_zhangsan.username == "张三_2"
    assert dingtalk_zhangsan.sso_name == "张三"


async def test_username_collision_with_local_name_only(session_maker):
    """存量用户只有 name 没有 username → 钉钉同名用户同样被唯一化"""
    snapshot = base_snapshot()
    async with session_maker() as session:
        session.add(UserModel(name="李四", role="viewer"))  # 无 username
        await session.commit()

    await _sync(session_maker, snapshot)
    u2 = await _user_by_dt(session_maker, "u2")
    assert u2.username == "李四_2"


# ============================================================================
# 7. 凭据未配置 → 400 / 构造即抛
# ============================================================================


def test_client_constructor_raises_without_credentials(monkeypatch):
    """app_key/app_secret 为空 → DingTalkClient 构造即抛 DingTalkError"""
    monkeypatch.setattr(type(config), "dingtalk_app_key", property(lambda self: ""))
    monkeypatch.setattr(type(config), "dingtalk_app_secret", property(lambda self: ""))
    with pytest.raises(DingTalkError):
        DingTalkClient()


async def test_sync_endpoint_400_without_credentials(api_env):
    """POST /api/dingtalk/sync：凭据未配置 → 400"未配置钉钉应用凭据" """
    # 建 admin（seed 的 admin 角色持有 manage:dingtalk:sync），
    # 直接用 jwt_utils 签发 access token 绕过登录（password_hash 为占位）
    async with api_env.maker() as session:
        session.add(
            UserModel(
                name="管理员",
                username="admin",
                password_hash="$2b$12$placeholder-not-a-real-hash-used-only-for-shape",
                role="admin",
            )
        )
        await session.commit()

    from opentask.jwt_utils import create_access_token

    async with api_env.maker() as session:
        admin = (
            await session.execute(select(UserModel).where(UserModel.username == "admin"))
        ).scalar_one()
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})

    resp = await api_env.client.post(
        "/api/dingtalk/sync", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400, resp.text
    assert "未配置钉钉应用凭据" in resp.json()["detail"]


async def test_sync_endpoint_requires_auth(api_env):
    """无 token → 401/403（路由已挂载且受认证保护）"""
    resp = await api_env.client.post("/api/dingtalk/sync")
    assert resp.status_code in (401, 403)


# ============================================================================
# 7.5 防御性：BFS 循环引用 / 分页死循环
# ============================================================================


async def test_bfs_survives_circular_dept_reference(session_maker):
    """钉钉数据异常（A 的子含 B、B 的子又含 A）→ BFS 不死循环，首次出现为准"""
    snapshot = base_snapshot()
    # 10↔11 互为父子：list_sub_depts(11) 会返回 dept 10，但 10 已 seen → 跳过
    snapshot["depts"].append({"dept_id": 10, "name": "研发部副本", "parent_id": 11, "order": 2})

    diff = await _sync(session_maker, snapshot)

    # 环未导致死循环；首次出现的 10（父=1）为准，副本被 seen 跳过
    assert diff["depts"] == {"created": 3, "updated": 0, "disabled": 0}
    async with session_maker() as session:
        rows = (
            await session.execute(
                select(Department).where(Department.dingtalk_dept_id == "10")
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].parent_id is None  # 仍是最初按 parent=1 建的根部门


async def test_bfs_terminates_on_direct_self_cycle(session_maker):
    """极端情况：部门的子包含自己 → 不死循环"""
    snapshot = base_snapshot()
    snapshot["depts"].append({"dept_id": 12, "name": "自环部", "parent_id": 1, "order": 3})
    snapshot["depts"].append({"dept_id": 12, "name": "自环部", "parent_id": 12, "order": 1})

    diff = await _sync(session_maker, snapshot)  # 若无 seen 防御会死循环超时
    assert diff["depts"]["created"] == 4


async def test_list_dept_users_repeated_cursor_raises():
    """next_cursor 停滞（与上一轮相同）→ DingTalkError，不无限分页"""
    client = DingTalkClient(app_key="fake-key", app_secret="fake-secret")

    async def fake_post(path, body):
        return {
            "list": [{"userid": f"u{body['cursor']}-{i}", "name": "x"} for i in range(2)],
            "has_more": True,
            "next_cursor": 5,  # 恒定不变 → 停滞
        }

    client._post = fake_post  # type: ignore[method-assign]
    with pytest.raises(DingTalkError, match="分页异常"):
        await client.list_dept_users(10)


async def test_list_dept_users_page_limit_raises():
    """页数超上限（1000 页）→ DingTalkError"""
    client = DingTalkClient(app_key="fake-key", app_secret="fake-secret")
    calls = {"n": 0}

    async def fake_post(path, body):
        calls["n"] += 1
        return {
            "list": [{"userid": f"u{calls['n']}-{i}", "name": "x"} for i in range(2)],
            "has_more": True,
            "next_cursor": calls["n"] * 100,
        }

    client._post = fake_post  # type: ignore[method-assign]
    with pytest.raises(DingTalkError, match="分页异常|页数上限"):
        await client.list_dept_users(10)
    assert calls["n"] == 1000  # 恰好在第 1000 页止损


async def test_list_dept_users_normal_pagination():
    """正常两页分页：cursor 推进 → 正常收敛返回"""
    client = DingTalkClient(app_key="fake-key", app_secret="fake-secret")

    async def fake_post(path, body):
        if body["cursor"] == 0:
            return {"list": [{"userid": "a", "name": "A"}], "has_more": True, "next_cursor": 100}
        return {"list": [{"userid": "b", "name": "B"}], "has_more": False, "next_cursor": 0}

    client._post = fake_post  # type: ignore[method-assign]
    users = await client.list_dept_users(10)
    assert [u["userid"] for u in users] == ["a", "b"]


# ============================================================================
# 8. migrate_service 改用公共 unique_username 后行为不变（回归见 tests/api/test_migrate_sso.py）
# 这里补一个公共函数直接单测
# ============================================================================


def test_unique_username_suffixing():
    """冲突时 _2/_3 递增；lower 归一化；不修改入参集合"""
    from opentask.services.user_center.utils import unique_username

    existing = {"admin", "wang", "wang_2"}
    assert unique_username(existing, "admin") == "admin_2"
    assert unique_username(existing, "WANG") == "WANG_3"
    assert unique_username(existing, "newbie") == "newbie"
    assert unique_username(set(), "") == "user"
    assert existing == {"admin", "wang", "wang_2"}  # 入参未被修改
