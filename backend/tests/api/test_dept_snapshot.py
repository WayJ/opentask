"""业务创建链路主部门快照写入测试（SQLite 内存库旁路 MySQL）

覆盖（code review J2 修复）：
1. developer（挂部门 A）创建 requirement/project/knowledge_base →
   行 dept_id == 主部门 A 的 id
2. 无部门用户创建 requirement → 行 dept_id NULL，且列表端 creator 兜底仍可见（SELF 档）
3. SELF 档用户（挂部门 A）创建 project → 行 dept_id 正确写入 A，
   但项目列表仍不可见（projects 无 created_by 兜底，预期语义：项目是部门资产）

注：tasks / agent_tasks 表含方言 ENUM/JSON 列（mysql ENUM / postgresql JSON），
SQLite 建表会炸——这两端的 dept_id 写入链路与本文件同构
（router 取主部门 → service/repo 可选参数 → 模型 dept_id 列），不在本文件直接断言。
issues 表同为 mysql ENUM，同样跳过（issues 创建端点已传 dept_id，代码级验证）。
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.app import App
from opentask.models.base import DBModel
from opentask.models.knowledge_base.model import KnowledgeBase
from opentask.models.requirement.model import Project, Requirement
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, UserDept
from opentask.repositories.base import get_session
from opentask.services.user_center.seed import seed_user_center

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 登录链路 + RBAC（角色/部门）+ 业务表（requirements 含编号序列表 / projects / knowledge_bases）
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
    "workspaces",
    "workspace_members",
    "requirements",
    "requirement_code_sequence",
    "projects",
    "project_members",
    "knowledge_bases",
)

REQUIREMENTS_URL = "/api/requirements"
PROJECTS_URL = "/api/projects"
KNOWLEDGE_BASES_URL = "/api/knowledge-bases"


@pytest_asyncio.fixture
async def scope():
    """SQLite 内存库 + dependency_overrides[get_session] 旁路 MySQL 的测试环境"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))

    maker = async_sessionmaker(engine, expire_on_commit=False)

    # Department.id 是 UUID 类型列——部门 id 必须用真实 UUID（否则结果处理阶段炸）
    dept_ids = {
        "A": str(uuid4()),
        "B": str(uuid4()),
    }

    # 播种系统角色（admin=ALL / developer=DEPT_AND_CHILD / viewer=SELF）
    async with maker() as session:
        await seed_user_center(session)
        # 造两个部门
        session.add(Department(id=dept_ids["A"], name="部门A", path="/dept-a"))
        session.add(Department(id=dept_ids["B"], name="部门B", path="/dept-b"))
        await session.commit()

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
        yield SimpleNamespace(client=client, maker=maker, dept_ids=dept_ids)

    app.dependency_overrides.clear()
    await engine.dispose()


async def _make_user(scope, *, username: str, role: str, dept_id: str | None = None) -> UserModel:
    """建一个带 bcrypt 哈希的本地用户（role 字符串走 RbacService 桥接），可选挂主部门"""
    async with scope.maker() as session:
        user = UserModel(
            name=f"用户-{username}",
            username=username,
            password_hash=_pwd.hash("Passw0rd123"),
            role=role,
        )
        session.add(user)
        await session.flush()
        if dept_id:
            session.add(UserDept(user_id=str(user.id), dept_id=dept_id, is_primary=True))
        await session.commit()
        found = (
            await session.execute(select(UserModel).where(UserModel.username == username))
        ).scalar_one()
        return found


async def _login_headers(scope, user: UserModel) -> dict:
    """用已建用户登录 → Authorization 头"""
    resp = await scope.client.post(
        "/api/auth/login-local",
        json={"userName": user.username, "password": "Passw0rd123"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['token']}"}


# ============================================================================
# 1. developer（挂部门 A）：三个创建端点都写入主部门快照
# ============================================================================

async def test_create_writes_primary_dept_snapshot(scope):
    """developer 建需求/项目/知识库 → 行 dept_id 均为主部门 A 的 id"""
    dev = await _make_user(scope, username="snap_dev", role="developer", dept_id=scope.dept_ids["A"])
    headers = await _login_headers(scope, dev)

    # 创建需求（created_by 走请求体，与现网前端行为一致）
    resp = await scope.client.post(
        REQUIREMENTS_URL,
        json={"title": "快照需求", "created_by": str(dev.id)},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    req_code = resp.json()["data"]["code"]

    # 创建项目
    resp = await scope.client.post(
        PROJECTS_URL, json={"name": "快照项目"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    proj_id = resp.json()["data"]["id"]

    # 创建知识库
    resp = await scope.client.post(
        KNOWLEDGE_BASES_URL, json={"name": "快照知识库"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    kb_id = resp.json()["data"]["id"]

    # 直接查行断言快照列
    async with scope.maker() as session:
        req = (
            await session.execute(select(Requirement).where(Requirement.code == req_code))
        ).scalar_one()
        proj = (
            await session.execute(select(Project).where(Project.id == proj_id))
        ).scalar_one()
        kb = (
            await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        ).scalar_one()

    assert req.dept_id == scope.dept_ids["A"]
    assert proj.dept_id == scope.dept_ids["A"]
    assert kb.dept_id == scope.dept_ids["A"]


# ============================================================================
# 2. 无部门用户：快照保持 NULL + requirements 列表 creator 兜底仍可见
# ============================================================================

async def test_create_without_dept_stays_null_with_creator_fallback(scope):
    """无部门用户（viewer/SELF）建需求 → dept_id NULL；列表靠 creator 兜底可见"""
    viewer = await _make_user(scope, username="snap_viewer_nodept", role="viewer")
    headers = await _login_headers(scope, viewer)

    resp = await scope.client.post(
        REQUIREMENTS_URL,
        json={"title": "无部门需求", "created_by": str(viewer.id)},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    req_code = resp.json()["data"]["code"]

    async with scope.maker() as session:
        req = (
            await session.execute(select(Requirement).where(Requirement.code == req_code))
        ).scalar_one()
    assert req.dept_id is None

    # SELF 档（空部门集）+ creator 兜底：本人创建的行仍可见
    resp = await scope.client.get(REQUIREMENTS_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    codes = {row["code"] for row in resp.json()["data"]["data"]}
    assert req_code in codes


# ============================================================================
# 3. SELF 档用户（挂部门 A）建项目：快照写入正确，但列表无兜底不可见
# ============================================================================

async def test_self_user_project_snapshot_written_but_invisible(scope):
    """SELF 档用户建项目 → 行 dept_id 正确写入 A；项目列表（无 creator 兜底）恒空"""
    # viewer 角色（SELF）但挂了部门 A：快照有值，可见性仍走空部门集
    scoped_viewer = await _make_user(
        scope, username="snap_viewer_dept", role="viewer", dept_id=scope.dept_ids["A"]
    )
    headers = await _login_headers(scope, scoped_viewer)

    resp = await scope.client.post(
        PROJECTS_URL, json={"name": "SELF档项目"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    proj_id = resp.json()["data"]["id"]

    async with scope.maker() as session:
        proj = (
            await session.execute(select(Project).where(Project.id == proj_id))
        ).scalar_one()
    assert proj.dept_id == scope.dept_ids["A"]

    # projects 无 created_by 归属列：SELF（空集）→ 恒空（部门资产语义）
    resp = await scope.client.get(PROJECTS_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    names = {row["name"] for row in resp.json()["data"]}
    assert names == set()


# ============================================================================
# 4. 创建端点未认证被拒（新增 authenticate 依赖不泄数据）
# ============================================================================

async def test_create_endpoints_require_auth(scope):
    """无 token 访问 4 个创建端点全部被拒（缺 token → 401 / 无效 token → 401）"""
    urls = [
        REQUIREMENTS_URL,
        PROJECTS_URL,
        KNOWLEDGE_BASES_URL,
        "/api/mission-center",
    ]
    for url in urls:
        resp = await scope.client.post(url, json={"title": "x", "name": "x"})
        assert resp.status_code == 401, f"{url} 缺 token 应返回 401，实际 {resp.status_code}"

        resp = await scope.client.post(
            url, json={"title": "x", "name": "x"}, headers={"Authorization": "Bearer bad"}
        )
        assert resp.status_code == 401, f"{url} 无效 token 应返回 401，实际 {resp.status_code}"
