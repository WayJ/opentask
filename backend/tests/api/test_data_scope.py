"""业务列表端点数据范围过滤测试（SQLite 内存库旁路 MySQL）

覆盖（Phase 3 Task 4）：
1. developer（DEPT_AND_CHILD，部门 A + 子部门 A1）→ requirements/projects/documents
   只见部门 A 行，不见部门 B 与 dept NULL 行
2. viewer（SELF）→ requirements 只见本人创建的（dept NULL 行），projects 恒空
3. admin（ALL）→ 全见
4. 无 token 访问 7 个列表端点 → 401
5. dept NULL 且 creator 为他人的行对 developer 不可见

注：tasks / agent_tasks 表含 MySQL 方言 ENUM 列，SQLite 建表会炸——
这两张表的过滤逻辑与 requirements/projects/documents 同走 apply_data_scope，
测试中跳过对这两端的直接数据断言（代码已改）。
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
from opentask.models.document.model import Document
from opentask.models.requirement.model import Project, Requirement
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, UserDept
from opentask.repositories.base import get_session
from opentask.services.user_center.seed import seed_user_center

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 登录链路 + RBAC（桥接/部门）+ 业务表（requirements/projects/documents）
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
    "requirements",
    "projects",
    "documents",
)

REQUIREMENTS_URL = "/api/requirements"
PROJECTS_URL = "/api/projects"
KNOWLEDGE_BASES_URL = "/api/knowledge-bases"
MISSION_CENTER_URL = "/api/mission-center"


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
        "A1": str(uuid4()),
        "B": str(uuid4()),
    }

    # 播种系统角色（admin=ALL / developer=DEPT_AND_CHILD / viewer=SELF）
    async with maker() as session:
        await seed_user_center(session)

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
    """建一个带 bcrypt 哈希的本地用户（role 字符串走 RbacService 桥接），可选挂部门"""
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


async def _seed_business_data(scope, *, dev_id: str, admin_id: str, viewer_id: str) -> dict:
    """造部门树（A 含子部门 A1、B）、需求 3 行、项目 2 行、文档 2 行

    requirements:
    - REQ_A:   dept=A,   creator=dev    （developer 可见）
    - REQ_B:   dept=B,   creator=admin  （仅 admin 可见）
    - REQ_NULL: dept=NULL, creator=viewer（仅 viewer 本人 / admin 可见）
    """
    async with scope.maker() as session:
        dept_a = Department(id=scope.dept_ids["A"], name="部门A", path="/dept-a")
        dept_a1 = Department(id=scope.dept_ids["A1"], name="部门A1", path="/dept-a/dept-a1")
        dept_b = Department(id=scope.dept_ids["B"], name="部门B", path="/dept-b")
        session.add_all([dept_a, dept_a1, dept_b])

        req_a = Requirement(
            code="REQ-A", title="需求A", tags=[], dept_id=scope.dept_ids["A"], created_by=dev_id
        )
        req_b = Requirement(
            code="REQ-B", title="需求B", tags=[], dept_id=scope.dept_ids["B"], created_by=admin_id
        )
        req_null = Requirement(
            code="REQ-NULL", title="需求无部门", tags=[], dept_id=None, created_by=viewer_id
        )
        session.add_all([req_a, req_b, req_null])

        proj_a = Project(name="项目A", dept_id=scope.dept_ids["A"], is_active=True)
        proj_b = Project(name="项目B", dept_id=scope.dept_ids["B"], is_active=True)
        session.add_all([proj_a, proj_b])

        await session.flush()

        # 两份文档都挂在 REQ_A 下，用 dept/creator 区分可见性
        doc_a = Document(
            entity_type="requirement",
            entity_id=req_a.id,
            file_path="a.pdf",
            file_name="a.pdf",
            file_type="application/pdf",
            file_size=1,
            dept_id=scope.dept_ids["A"],
            created_by=dev_id,
        )
        doc_b = Document(
            entity_type="requirement",
            entity_id=req_a.id,
            file_path="b.pdf",
            file_name="b.pdf",
            file_type="application/pdf",
            file_size=1,
            dept_id=scope.dept_ids["B"],
            created_by=viewer_id,
        )
        session.add_all([doc_a, doc_b])
        await session.commit()

        return {
            "req_a": req_a.id,
            "req_b": req_b.id,
            "req_null": req_null.id,
        }


async def _setup_all(scope) -> dict:
    """一次性建 3 用户（admin/developer/viewer）+ 业务数据，返回 id 集合"""
    admin = await _make_user(scope, username="scope_admin", role="admin")
    dev = await _make_user(
        scope, username="scope_dev", role="developer", dept_id=scope.dept_ids["A"]
    )
    viewer = await _make_user(scope, username="scope_viewer", role="viewer")
    ids = await _seed_business_data(
        scope, dev_id=str(dev.id), admin_id=str(admin.id), viewer_id=str(viewer.id)
    )
    return {"admin": admin, "dev": dev, "viewer": viewer, **ids}


async def _requirement_ids(scope, headers) -> set[str]:
    """GET /api/requirements → 可见需求 id 集"""
    resp = await scope.client.get(REQUIREMENTS_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    return {row["id"] for row in resp.json()["data"]["data"]}


async def _project_names(scope, headers) -> set[str]:
    """GET /api/projects → 可见项目名集"""
    resp = await scope.client.get(PROJECTS_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    return {row["name"] for row in resp.json()["data"]}


async def _document_names(scope, headers, requirement_id: str) -> set[str]:
    """GET /api/requirements/{id}/documents → 可见文档名集"""
    resp = await scope.client.get(f"{REQUIREMENTS_URL}/{requirement_id}/documents", headers=headers)
    assert resp.status_code == 200, resp.text
    return {row["file_name"] for row in resp.json()["data"]["data"]}


# ============================================================================
# 1. developer：DEPT_AND_CHILD（A + A1）
# ============================================================================

async def test_developer_dept_and_child(scope):
    """developer 可见部门 A+A1：见 deptA 需求/项目/文档，不见 deptB 与 dept NULL"""
    ctx = await _setup_all(scope)
    headers = await _login_headers(scope, ctx["dev"])

    # 需求：deptA 行可见；deptB / dept NULL（creator 是 viewer）不可见
    ids = await _requirement_ids(scope, headers)
    assert ids == {ctx["req_a"]}

    # 项目：deptA 可见，deptB 不可见
    assert await _project_names(scope, headers) == {"项目A"}

    # 文档：挂在 REQ_A 下的两份，deptA 的可见，deptB 的不可见（creator 是 viewer）
    docs = await _document_names(scope, headers, ctx["req_a"])
    assert docs == {"a.pdf"}


# ============================================================================
# 2. viewer：SELF
# ============================================================================

async def test_viewer_self(scope):
    """viewer（SELF）：需求只见本人创建的 dept NULL 行；项目恒空（无 creator 旁路）"""
    ctx = await _setup_all(scope)
    headers = await _login_headers(scope, ctx["viewer"])

    ids = await _requirement_ids(scope, headers)
    assert ids == {ctx["req_null"]}

    # 项目表无 created_by 归属列：SELF（空集）→ 恒空
    assert await _project_names(scope, headers) == set()

    # 文档：deptB 的那份 creator 是 viewer 本人 → 可见；deptA 的不可见
    docs = await _document_names(scope, headers, ctx["req_a"])
    assert docs == {"b.pdf"}


# ============================================================================
# 3. admin：ALL
# ============================================================================

async def test_admin_all(scope):
    """admin（ALL 档零过滤）：需求 3 行、项目 2 个、文档 2 份全见"""
    ctx = await _setup_all(scope)
    headers = await _login_headers(scope, ctx["admin"])

    ids = await _requirement_ids(scope, headers)
    assert ids == {ctx["req_a"], ctx["req_b"], ctx["req_null"]}

    assert await _project_names(scope, headers) == {"项目A", "项目B"}

    docs = await _document_names(scope, headers, ctx["req_a"])
    assert docs == {"a.pdf", "b.pdf"}


# ============================================================================
# 4. 无 token → 401
# ============================================================================

async def test_unauthenticated_rejected(scope):
    """无 token 访问 7 个列表端点全部被拒（本期预期的破坏性变更）

    缺失 Authorization 头 → HTTPBearer auto_error 默认 403；
    无效 token → 401。两种情况均不得泄出列表数据。
    """
    ctx = await _setup_all(scope)

    urls = [
        REQUIREMENTS_URL,
        "/api/issues",
        PROJECTS_URL,
        KNOWLEDGE_BASES_URL,
        f"{REQUIREMENTS_URL}/{ctx['req_a']}/tasks",
        f"{REQUIREMENTS_URL}/{ctx['req_a']}/documents",
        MISSION_CENTER_URL,
    ]
    for url in urls:
        resp = await scope.client.get(url)
        assert resp.status_code == 403, f"{url} 缺 token 应返回 403，实际 {resp.status_code}"

        resp = await scope.client.get(url, headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401, f"{url} 无效 token 应返回 401，实际 {resp.status_code}"


# ============================================================================
# 5. dept NULL 行对 developer 不可见（creator 是他人）
# ============================================================================

async def test_null_dept_row_invisible_to_developer(scope):
    """dept NULL 行不在任何可见部门集内，且 creator 是 viewer（他人）→ developer 不可见"""
    ctx = await _setup_all(scope)
    headers = await _login_headers(scope, ctx["dev"])

    ids = await _requirement_ids(scope, headers)
    assert ctx["req_null"] not in ids
    # 同行对 creator 本人（viewer，SELF）可见——dept NULL 不影响 creator 旁路
    viewer_headers = await _login_headers(scope, ctx["viewer"])
    viewer_ids = await _requirement_ids(scope, viewer_headers)
    assert ctx["req_null"] in viewer_ids
