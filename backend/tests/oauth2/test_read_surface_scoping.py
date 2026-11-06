"""只读数据面的数据范围测试（部门可见集收窄）

背景：``/oauth2/api/tasks`` 曾直接复用契约层 ``/tasks`` 的取数（无部门可见性
过滤），会把**整个工作区**的任务集暴露给只读 scope。改走通用 issue service
的取数路径后，本组用例把「按成员可见集收窄」钉死——同一工作区两个不同部门的
成员，各自的 OAuth token 只能拿到自己可见集内的任务。
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, Role, UserDept, UserRole
from opentask.services.oauth2.client_service import OAuthClientService
from opentask.services.oauth2.token_service import OAuthTokenService

from .conftest import READ_SCOPES, REDIRECT_URI


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


async def _seed_department(session: AsyncSession, name: str, path: str) -> Department:
    department = Department(name=name, path=path, sort=0, status=1)
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def _seed_role(session: AsyncSession, code: str) -> Role:
    """DEPT 数据范围的角色（只看所属部门，不含子树）"""
    role = Role(code=code, name="部门范围角色", description=None, data_scope="DEPT", status=1)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


async def _seed_member(
    session: AsyncSession, role: Role, department: Department, tag: str
) -> UserModel:
    """成员：属部门 + 持 DEPT 范围角色"""
    user = UserModel(
        name=f"范围成员 {tag}",
        username=f"scope_member_{tag}",
        password_hash=None,
        role="viewer",
        status=1,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    session.add(UserDept(user_id=str(user.id), dept_id=str(department.id), is_primary=True))
    session.add(UserRole(user_id=str(user.id), role_id=str(role.id)))
    await session.commit()
    return user


# issue_code 序号（同会话内唯一）：E99 Jira 投影只认 KEY-N（序号 < 1e6）。
_SEQ = [800_000]


def _next_issue_code() -> str:
    _SEQ[0] += 1
    return f"OT-{_SEQ[0]}"


async def _seed_issue(
    session: AsyncSession, title: str, owner: UserModel, department: Department
) -> Issue:
    issue = Issue(
        issue_code=_next_issue_code(),
        title=title,
        description=None,
        type="bug",
        status="open",
        priority="medium",
        assignee_id=None,
        reporter_id=str(owner.id),
        created_by=str(owner.id),
        dept_id=str(department.id),
    )
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return issue


@pytest_asyncio.fixture
async def issue_cleanup(test_session: AsyncSession):
    """用例自清理：本目录造的行不留在共享测试库里

    全局 conftest 只在会话收尾删表，**会话内**残留会影响后续用例的计数断言
    （如 Jira 线格式的 JQL 分页用例按 issues 表计数）。
    """
    created: list[str] = []

    def track(issue: Issue) -> Issue:
        created.append(issue.id)
        return issue

    yield track
    if created:
        await test_session.execute(
            Issue.__table__.delete().where(Issue.id.in_(created))
        )
        await test_session.commit()


@pytest.mark.asyncio
async def test_read_tasks_scoped_to_member_visible_departments(
    test_client: AsyncClient, test_session: AsyncSession, issue_cleanup
):
    """两个不同部门的成员，各自的 OAuth token 只拿到自己可见集内的任务"""
    suffix = _suffix()
    dept_a = await _seed_department(test_session, f"范围部门甲 {suffix}", f"/oauth-scope/{suffix}/a")
    dept_b = await _seed_department(test_session, f"范围部门乙 {suffix}", f"/oauth-scope/{suffix}/b")
    role = await _seed_role(test_session, f"scope_dept_role_{suffix}")
    member_a = await _seed_member(test_session, role, dept_a, f"a_{suffix}")
    member_b = await _seed_member(test_session, role, dept_b, f"b_{suffix}")

    issue_a = issue_cleanup(await _seed_issue(test_session, f"部门甲的任务 {suffix}", member_a, dept_a))
    issue_b = issue_cleanup(await _seed_issue(test_session, f"部门乙的任务 {suffix}", member_b, dept_b))

    client, _secret = await OAuthClientService(test_session).register(
        client_id=f"scope-client-{suffix}",
        name="可见集范围用例",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(member_a.id),
    )
    token_a = await OAuthTokenService(test_session).issue(
        user=member_a, client_id=client.client_id, scope="read:tasks"
    )
    token_b = await OAuthTokenService(test_session).issue(
        user=member_b, client_id=client.client_id, scope="read:tasks"
    )

    response_a = await test_client.get(
        "/oauth2/api/tasks",
        headers={"Authorization": f"Bearer {token_a['access_token']}"},
    )
    assert response_a.status_code == 200, response_a.text
    ids_a = {item["id"] for item in response_a.json()["items"]}
    assert issue_a.id in ids_a, "本人部门的任务应当可见"
    assert issue_b.id not in ids_a, "越界部门（他人部门）的任务不得可见"

    response_b = await test_client.get(
        "/oauth2/api/tasks",
        headers={"Authorization": f"Bearer {token_b['access_token']}"},
    )
    assert response_b.status_code == 200, response_b.text
    ids_b = {item["id"] for item in response_b.json()["items"]}
    assert issue_b.id in ids_b, "本人部门的任务应当可见"
    assert issue_a.id not in ids_b, "越界部门（他人部门）的任务不得可见"


@pytest.mark.asyncio
async def test_read_tasks_status_filter_uses_native_issue_status(
    test_client: AsyncClient, test_session: AsyncSession, issue_cleanup
):
    """status 参数取 OpenTask 原生 IssueStatus 词表（不再是契约层通用词表）"""
    suffix = _suffix()
    department = await _seed_department(test_session, f"状态过滤部门 {suffix}", f"/oauth-scope/{suffix}/s")
    role = await _seed_role(test_session, f"scope_status_role_{suffix}")
    member = await _seed_member(test_session, role, department, f"s_{suffix}")
    open_issue = issue_cleanup(
        await _seed_issue(test_session, f"进行中任务 {suffix}", member, department)
    )

    closed = Issue(
        issue_code=_next_issue_code(),
        title=f"已关闭任务 {suffix}",
        description=None,
        type="bug",
        status="closed",
        priority="medium",
        assignee_id=None,
        reporter_id=str(member.id),
        created_by=str(member.id),
        dept_id=str(department.id),
    )
    test_session.add(closed)
    await test_session.commit()
    await test_session.refresh(closed)
    issue_cleanup(closed)

    client, _secret = await OAuthClientService(test_session).register(
        client_id=f"scope-status-client-{suffix}",
        name="状态过滤用例",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(member.id),
    )
    token = await OAuthTokenService(test_session).issue(
        user=member, client_id=client.client_id, scope="read:tasks"
    )
    headers = {"Authorization": f"Bearer {token['access_token']}"}

    only_open = await test_client.get("/oauth2/api/tasks", params={"status": "open"}, headers=headers)
    assert only_open.status_code == 200, only_open.text
    ids = {item["id"] for item in only_open.json()["items"]}
    assert open_issue.id in ids
    assert closed.id not in ids

    # 未知状态 → 400 invalid_status（不是静默忽略）
    unknown = await test_client.get("/oauth2/api/tasks", params={"status": "not-a-status"}, headers=headers)
    assert unknown.status_code == 400
    assert unknown.json()["detail"]["error"] == "invalid_status"


@pytest.mark.asyncio
async def test_read_tasks_unaligned_offset_returns_exact_window(
    test_client: AsyncClient, test_session: AsyncSession, issue_cleanup
):
    """offset 不是 limit 的整数倍时，窗口必须从全局第 offset 条起

    limit=10、offset=15：调用方要全局第 15–24 条。错误算法会把 page_size
    加成 limit+remainder，service 从第 15 条再取 15 条后切 [5:]，得到第 20 条起。
    """
    from datetime import datetime, timedelta

    suffix = _suffix()
    department = await _seed_department(
        test_session, f"窗口部门 {suffix}", f"/oauth-scope/{suffix}/w"
    )
    role = await _seed_role(test_session, f"scope_window_role_{suffix}")
    member = await _seed_member(test_session, role, department, f"w_{suffix}")

    seeded = []
    base = datetime(2026, 1, 1, 0, 0, 0)
    for index in range(30):
        issue = Issue(
            issue_code=_next_issue_code(),
            title=f"窗口任务 {suffix} {index:02d}",
            description=None,
            type="bug",
            status="open",
            priority="medium",
            assignee_id=None,
            reporter_id=str(member.id),
            created_by=str(member.id),
            dept_id=str(department.id),
            created_at=base + timedelta(seconds=index),
        )
        test_session.add(issue)
        await test_session.commit()
        await test_session.refresh(issue)
        seeded.append(issue_cleanup(issue))

    client, _secret = await OAuthClientService(test_session).register(
        client_id=f"scope-window-client-{suffix}",
        name="非对齐窗口用例",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(member.id),
    )
    token = await OAuthTokenService(test_session).issue(
        user=member, client_id=client.client_id, scope="read:tasks"
    )
    response = await test_client.get(
        "/oauth2/api/tasks",
        params={"limit": 10, "offset": 15},
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 200, response.text
    ids = [item["id"] for item in response.json()["items"]]
    expected = [issue.id for issue in seeded[15:25]]
    assert ids == expected
