"""业务表 dept_id 历史回填测试（SQLite 内存库旁路 MySQL）

覆盖（Phase 6 Task 1，spec 4.3）：
1. requirements/documents/issues 三表回填：
   - created_by 匹配优先级：UUID 精确 id / username / name → 均回填主部门
   - 匹配到用户但无任何部门归属 → 保持 NULL 计 skipped_no_dept
   - 脏值（'system'/'admin'/已删用户 id）→ 保持 NULL 计 skipped_dirty
   - name 重名（两个"王五"）→ 跳过计 skipped_ambiguous
   - created_by 为 NULL → 计 skipped_no_owner
2. projects（及 knowledge_bases/tasks）无 created_by → 全表 skipped_no_owner，不回填
3. agent_tasks 含 MySQL 方言 ENUM 列，SQLite 建不了表 → 报告 table_missing=True
4. 幂等：重跑全表 updated=0，已回填行 dept_id 不变
5. 无 manage:user:migrate 权限（viewer）→ 403
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.dialects.mysql import ENUM as MySQLEnum
from sqlalchemy import String
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.app import App
from opentask.models.base import DBModel
# issues/documents 模型不在 opentask.models.__init__ 全量导出内，显式注册
from opentask.models.document.model import Document as DocumentModel  # noqa: F401
from opentask.models.issue.model import Issue as IssueModel  # noqa: F401
from opentask.models.knowledge_base.model import KnowledgeBase
from opentask.models.requirement.model import Project, Requirement
from opentask.models.task.model import Task
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, UserDept
from opentask.repositories.base import get_session
from opentask.services.user_center.seed import seed_user_center

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 登录链路 + RBAC + 部门归属 + 业务表（agent_tasks 含 mysql ENUM，SQLite 建不了）
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
    "issues",
    "projects",
    "knowledge_bases",
    "documents",
    "tasks",
)

BACKFILL_URL = "/api/user-center/backfill/dept-id"


@pytest_asyncio.fixture
async def bf():
    """SQLite 内存库 + dependency_overrides[get_session] 旁路 MySQL 的测试环境"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]

    # issues 的 type/status/priority 是 MySQL 方言 ENUM，SQLite 编译会炸——
    # 临时挂 sqlite variant（String）建表，建完立即还原，不污染全局 metadata
    patched: list[tuple[object, object]] = []
    for table in tables:
        for col in table.columns:
            if isinstance(col.type, MySQLEnum):
                patched.append((col, col.type))
                col.type = col.type.with_variant(String(255), "sqlite")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
    finally:
        for col, original in patched:
            col.type = original

    maker = async_sessionmaker(engine, expire_on_commit=False)

    # 播种系统角色与权限点（require_permission 权限门槛的数据来源）
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
        yield SimpleNamespace(client=client, maker=maker)

    app.dependency_overrides.clear()
    await engine.dispose()


def _new_user(*, username: str, name: str | None = None,
              role: str = "viewer") -> UserModel:
    """构造本地用户（bcrypt 哈希，role 字符串走 RbacService 桥接）"""
    return UserModel(
        name=name,
        username=username,
        password_hash=_pwd.hash("Passw0rd123"),
        role=role,
    )


async def _login_headers(bf, username: str) -> dict:
    resp = await bf.client.post(
        "/api/auth/login-local", json={"userName": username, "password": "Passw0rd123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['token']}"}


async def _seed(bf, dept_a: str) -> dict:
    """造部门 + 用户 + 业务数据，返回关键 id/值

    用户：
    - zhangsan（张三，主部门 A）：三种 created_by 写法都应匹配到他
    - lisi（李四，无任何部门）：匹配到但无归属 → skipped_no_dept
    - wangwu1 / wangwu2（都叫"王五"）：name 重名 → skipped_ambiguous
    - backfill_admin：调用方（admin 角色），注意 username 不叫 "admin"——
      "admin" 作为 created_by 值必须是脏值（无此用户）
    """
    async with bf.maker() as session:
        session.add(Department(id=dept_a, name="部门A", path="/dept-a"))

        zhangsan = _new_user(username="zhangsan", name="张三")
        lisi = _new_user(username="lisi", name="李四")
        wangwu1 = _new_user(username="wangwu1", name="王五")
        wangwu2 = _new_user(username="wangwu2", name="王五")
        admin = _new_user(username="backfill_admin", name="回填管理员", role="admin")
        session.add_all([zhangsan, lisi, wangwu1, wangwu2, admin])
        await session.flush()
        # 张三挂主部门 A
        session.add(UserDept(user_id=str(zhangsan.id), dept_id=dept_a, is_primary=True))

        deleted_id = str(uuid4())  # 已删用户的 id（库里不存在）

        # requirements：7 行 dept NULL + 1 行已有部门（不应被动）
        reqs = {
            "by_id": Requirement(code="R-ID", title="按id", tags=[],
                                 created_by=str(zhangsan.id)),
            "by_username": Requirement(code="R-UN", title="按用户名", tags=[],
                                       created_by="zhangsan"),
            "by_name": Requirement(code="R-NM", title="按姓名", tags=[],
                                   created_by="张三"),
            "no_dept": Requirement(code="R-ND", title="无归属", tags=[],
                                   created_by="lisi"),
            "system": Requirement(code="R-SY", title="系统", tags=[],
                                  created_by="system"),
            "deleted": Requirement(code="R-DL", title="已删用户", tags=[],
                                   created_by=deleted_id),
            "ambiguous": Requirement(code="R-AM", title="重名", tags=[],
                                     created_by="王五"),
            "already": Requirement(code="R-OK", title="已有部门", tags=[],
                                   dept_id=dept_a, created_by=str(zhangsan.id)),
        }
        session.add_all(reqs.values())

        # documents：按姓名回填 / 脏值 admin / 空 owner
        docs = {
            "by_name": DocumentModel(
                entity_type="requirement", entity_id=str(uuid4()),
                file_path="a.pdf", file_name="a.pdf",
                file_type="application/pdf", file_size=1, created_by="张三",
            ),
            "admin": DocumentModel(
                entity_type="requirement", entity_id=str(uuid4()),
                file_path="b.pdf", file_name="b.pdf",
                file_type="application/pdf", file_size=1, created_by="admin",
            ),
            "no_owner": DocumentModel(
                entity_type="requirement", entity_id=str(uuid4()),
                file_path="c.pdf", file_name="c.pdf",
                file_type="application/pdf", file_size=1, created_by=None,
            ),
        }
        session.add_all(docs.values())

        # issues：按 id 回填 / 脏值
        issues = {
            "by_id": IssueModel(
                issue_code="ISS-1", title="i1", type="bug", reporter_id="r1",
                created_by=str(zhangsan.id),
            ),
            "dirty": IssueModel(
                issue_code="ISS-2", title="i2", type="bug", reporter_id="r1",
                created_by="ghost-user",
            ),
        }
        session.add_all(issues.values())

        # 无 created_by 的表：全表 skipped_no_owner
        session.add_all([
            Project(name="项目A"),
            Project(name="项目B"),
            KnowledgeBase(name="KB-A"),
            Task(title="任务A", requirement_id=str(uuid4())),
        ])
        await session.commit()

        return {"zhangsan_id": str(zhangsan.id), "deleted_id": deleted_id}


async def _call_backfill(bf) -> dict:
    headers = await _login_headers(bf, "backfill_admin")
    resp = await bf.client.post(BACKFILL_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ============================================================================
# 1. requirements：三种匹配优先级 + 无归属 + 脏值 + 重名 + 已有部门不动
# ============================================================================

async def test_backfill_requirements(bf):
    dept_a = str(uuid4())
    ctx = await _seed(bf, dept_a)
    report = await _call_backfill(bf)

    r = report["requirements"]
    assert r["total_null"] == 7  # 已有部门的 R-OK 不在 NULL 统计内
    assert r["updated"] == 3     # id / username / name 三种写法
    assert r["skipped_no_dept"] == 1
    assert r["skipped_ambiguous"] == 1
    assert r["skipped_dirty_count"] == 2  # 'system' + 已删用户 id
    assert r["skipped_no_owner"] == 0
    assert sorted(r["dirty_samples"]) == sorted(["system", ctx["deleted_id"]])

    # 库内校验：三种匹配都写主部门 A，其余保持 NULL
    async with bf.maker() as session:
        rows = {
            req.code: req.dept_id
            for req in (await session.execute(select(Requirement))).scalars()
        }
    assert rows["R-ID"] == dept_a
    assert rows["R-UN"] == dept_a
    assert rows["R-NM"] == dept_a
    assert rows["R-ND"] is None
    assert rows["R-SY"] is None
    assert rows["R-DL"] is None
    assert rows["R-AM"] is None
    assert rows["R-OK"] == dept_a  # 已有部门不动


# ============================================================================
# 1. documents / issues
# ============================================================================

async def test_backfill_documents_and_issues(bf):
    dept_a = str(uuid4())
    await _seed(bf, dept_a)
    report = await _call_backfill(bf)

    d = report["documents"]
    assert d["total_null"] == 3
    assert d["updated"] == 1
    assert d["skipped_dirty_count"] == 1  # 'admin' 无此用户（调用方不叫 admin）
    assert d["skipped_no_owner"] == 1     # created_by 为 NULL
    assert d["dirty_samples"] == ["admin"]

    i = report["issues"]
    assert i["total_null"] == 2
    assert i["updated"] == 1
    assert i["skipped_dirty_count"] == 1
    assert i["dirty_samples"] == ["ghost-user"]

    async with bf.maker() as session:
        doc_rows = {
            doc.file_name: doc.dept_id
            for doc in (await session.execute(select(DocumentModel))).scalars()
        }
        issue_rows = {
            iss.issue_code: iss.dept_id
            for iss in (await session.execute(select(IssueModel))).scalars()
        }
    assert doc_rows["a.pdf"] == dept_a
    assert doc_rows["b.pdf"] is None
    assert doc_rows["c.pdf"] is None
    assert issue_rows["ISS-1"] == dept_a
    assert issue_rows["ISS-2"] is None


# ============================================================================
# 2. 无 created_by 的表：全表 skipped_no_owner，不回填
# ============================================================================

async def test_backfill_no_owner_tables(bf):
    dept_a = str(uuid4())
    await _seed(bf, dept_a)
    report = await _call_backfill(bf)

    projects = report["projects"]
    assert projects["total_null"] == 2
    assert projects["skipped_no_owner"] == 2
    assert projects["updated"] == 0

    assert report["knowledge_bases"] == {
        "total_null": 1, "updated": 0, "skipped_no_dept": 0,
        "skipped_no_owner": 1, "skipped_ambiguous": 0,
        "skipped_dirty_count": 0, "dirty_samples": [], "table_missing": False,
    }
    assert report["tasks"]["skipped_no_owner"] == 1
    assert report["tasks"]["updated"] == 0

    async with bf.maker() as session:
        project = (
            await session.execute(select(Project).where(Project.name == "项目A"))
        ).scalar_one()
    assert project.dept_id is None


# ============================================================================
# 3. agent_tasks：SQLite 建不了 mysql ENUM 表 → table_missing
# ============================================================================

async def test_backfill_agent_tasks_missing_on_sqlite(bf):
    await _seed(bf, str(uuid4()))
    report = await _call_backfill(bf)
    assert report["agent_tasks"]["table_missing"] is True
    assert report["agent_tasks"]["updated"] == 0


# ============================================================================
# 4. 幂等：重跑全表 updated=0，已回填行不变
# ============================================================================

async def test_backfill_idempotent(bf):
    dept_a = str(uuid4())
    await _seed(bf, dept_a)
    first = await _call_backfill(bf)
    assert first["requirements"]["updated"] == 3

    second = await _call_backfill(bf)
    for table_name, entry in second.items():
        assert entry["updated"] == 0, f"{table_name} 重跑应无更新"
    # 保持 NULL 的行仍被如实统计（requirements 剩 no_dept 1 + dirty 2 + ambiguous 1 = 4）
    r = second["requirements"]
    assert r["total_null"] == 4
    assert r["skipped_no_dept"] == 1
    assert r["skipped_dirty_count"] == 2
    assert r["skipped_ambiguous"] == 1

    async with bf.maker() as session:
        rows = {
            req.code: req.dept_id
            for req in (await session.execute(select(Requirement))).scalars()
        }
    assert rows["R-ID"] == dept_a   # 已回填值不被覆盖
    assert rows["R-SY"] is None


# ============================================================================
# 5. 无 manage:user:migrate 权限 → 403
# ============================================================================

async def test_backfill_forbidden_for_viewer(bf):
    await _seed(bf, str(uuid4()))
    headers = await _login_headers(bf, "lisi")  # viewer

    resp = await bf.client.post(BACKFILL_URL, headers=headers)
    assert resp.status_code == 403
    assert "权限不足" in resp.json()["detail"]
