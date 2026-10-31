"""Jira 线格式往返测试（S7：/rest/api/2/*，Orca Jira 集成兼容层）

覆盖（探测报告 docs/superpowers/sprints/2026-11-01-S7-orca-jira-probe.md
为形状依据）：
- 鉴权：Basic base64(user:vk_) / Bearer vk_ → 契约 access_token 内核；
  缺凭证 / 坏凭证 → 401 Jira 形状错误体（errorMessages 含 CONTRACT_AUTH_*）
- 五操作往返：create → search(JQL) → get → update → transition，
  每步的 Jira 形状（key/fields/status.statusCategory/204 等）逐字段断言
- key 编解码：OPENTASK-{年*100000+序号} ↔ issue_code 单射往返
- JQL 子集：Orca list 自产 JQL（currentUser/statusCategory/ORDER BY）、
  key=/in、summary ~、project 别名空集、sprint 空集；子集外 400
- 评论：POST/GET + startAt 翻页（Orca BB 读法）
- 元数据：project/priority/createmeta types/fields/myself
- 落库核验：状态流转写 timeline（status_changed）

挂载路径（/rest/api/2 经 ASGI 转发路由在主 App 下）随主 App 客户端打，
转发、前缀剥离、子应用异常处理器都在真实链路上验证。
"""

import base64
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from opentask.app import App
from opentask.api.jira import jira_app
from opentask.api.jira.auth import authenticate_jira
from opentask.api.jira.keys import issue_code_to_key, key_to_issue_code
from opentask.models.issue.model import Issue, IssueTimeline
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session

from .conftest import TITLE_PREFIX, create_api_key, seed_issue


# ============================================================================
# 客户端 fixture：主 App（转发路由）+ 子应用依赖覆盖（会话指向测试 PG）
# ============================================================================


@pytest_asyncio.fixture
async def jira_setup(pg_engine: AsyncEngine, test_user: UserModel):
    """子应用依赖覆盖：get_session → 测试 PG；authenticate_jira → 测试用户"""
    maker = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )

    async def override_get_session():
        session = maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def override_auth() -> UserModel:
        return test_user

    jira_app.dependency_overrides[get_session] = override_get_session
    jira_app.dependency_overrides[authenticate_jira] = override_auth
    yield test_user
    jira_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def jira_client(
    jira_setup: UserModel, contract_app: App
) -> AsyncGenerator[AsyncClient, None]:
    """经主 App 转发路由打 /rest/api/2/*（鉴权已覆盖为测试用户）"""
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def jira_raw_client(
    jira_setup: UserModel, contract_app: App
) -> AsyncGenerator[AsyncClient, None]:
    """不覆盖鉴权的客户端：打真实 Basic/Bearer 校验链（对测试 PG）"""
    jira_app.dependency_overrides.pop(authenticate_jira, None)
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        yield ac


def _basic_header(username: str, token: str) -> str:
    return "Basic " + base64.b64encode(f"{username}:{token}".encode()).decode()


# ============================================================================
# key 编解码（纯单元）
# ============================================================================


class TestKeyCodec:
    def test_roundtrip(self):
        assert issue_code_to_key("ISSUE2026-3") == "OPENTASK-2026000000003"
        assert key_to_issue_code("OPENTASK-2026000000003") == "ISSUE2026-3"

    def test_key_case_insensitive_prefix(self):
        assert key_to_issue_code("opentask-2026000000003") == "ISSUE2026-3"

    def test_bad_shapes_rejected(self):
        with pytest.raises(ValueError):
            key_to_issue_code("ENG-1")
        with pytest.raises(ValueError):
            key_to_issue_code("OPENTASK-xyz")
        with pytest.raises(ValueError):
            issue_code_to_key("2026-3")

    def test_seq_overflow_rejected(self):
        with pytest.raises(ValueError):
            issue_code_to_key("ISSUE2026-1000000000")


# ============================================================================
# 鉴权（真实链路）
# ============================================================================


class TestJiraAuth:
    async def test_myself_bearer_api_key(self, jira_raw_client, db, jira_setup):
        key = await create_api_key(db, jira_setup)
        resp = await jira_raw_client.get(
            "/rest/api/2/myself", headers={"Authorization": f"Bearer {key}"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == jira_setup.username
        assert body["displayName"]
        assert body["active"] is True

    async def test_myself_basic_user_token(self, jira_raw_client, db, jira_setup):
        """Basic 的密码位即 API Key；用户名位不参与校验（探测 §5）"""
        key = await create_api_key(db, jira_setup)
        resp = await jira_raw_client.get(
            "/rest/api/2/myself",
            headers={"Authorization": _basic_header("anything", key)},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == jira_setup.username

    async def test_missing_credentials_401_jira_body(self, jira_raw_client):
        resp = await jira_raw_client.get("/rest/api/2/myself")
        assert resp.status_code == 401
        body = resp.json()
        assert "errorMessages" in body and "errors" in body
        assert body["errorMessages"][0].startswith("CONTRACT_AUTH_MISSING")
        assert resp.headers.get("www-authenticate")

    async def test_invalid_token_401(self, jira_raw_client):
        resp = await jira_raw_client.get(
            "/rest/api/2/myself", headers={"Authorization": "Bearer vk_nope"}
        )
        assert resp.status_code == 401
        assert resp.json()["errorMessages"][0].startswith("CONTRACT_AUTH_INVALID")

    async def test_broken_basic_401(self, jira_raw_client):
        resp = await jira_raw_client.get(
            "/rest/api/2/myself",
            headers={"Authorization": "Basic ###not-base64###"},
        )
        assert resp.status_code == 401
        assert resp.json()["errorMessages"][0].startswith("CONTRACT_AUTH_MISSING")

    async def test_unknown_scheme_401(self, jira_raw_client):
        resp = await jira_raw_client.get(
            "/rest/api/2/myself", headers={"Authorization": "Token abc"}
        )
        assert resp.status_code == 401
        assert "Basic 或 Bearer" in resp.json()["errorMessages"][0]


# ============================================================================
# 五操作往返：create → search → get → update → transition
# ============================================================================


class TestJiraWireRoundTrip:
    async def test_full_round_trip(
        self, jira_client, db, jira_setup, assignee_user
    ):
        # --- 创建（探测 §3：POST /issue {fields}，响应 {id,key}）---
        # assignee = currentUser() 过滤的是负责人 → 创建时即分配给操作者
        resp = await jira_client.post(
            "/rest/api/2/issue",
            json={
                "fields": {
                    "project": {"id": "OPENTASK"},
                    "issuetype": {"id": "bug"},
                    "summary": f"{TITLE_PREFIX}Jira线创建",
                    "description": "描述文本",
                    "assignee": {"name": jira_setup.username},
                    "labels": ["ct-jira-wire"],
                }
            },
        )
        assert resp.status_code == 201, resp.text
        created = resp.json()
        assert created["key"].startswith("OPENTASK-")
        assert created["id"]

        # --- 列表（Orca list --filter assigned 的自产 JQL，探测 §4）---
        jql = (
            "assignee = currentUser() AND statusCategory != Done "
            "ORDER BY updated DESC"
        )
        resp = await jira_client.post(
            "/rest/api/2/search",
            json={"jql": jql, "maxResults": 50, "fields": ["summary", "status"]},
        )
        assert resp.status_code == 200, resp.text
        search = resp.json()
        assert search["total"] >= 1
        mine = [i for i in search["issues"] if i["key"] == created["key"]]
        assert mine, "currentUser() 未命中创建人（reporter/assignee 语义）"
        fields = mine[0]["fields"]
        assert fields["summary"] == f"{TITLE_PREFIX}Jira线创建"
        assert fields["status"]["statusCategory"]["key"] == "new"
        assert "ct-jira-wire" in fields["labels"]

        # --- 读取（GET /issue/{key}，fields/renderedFields 形状）---
        resp = await jira_client.get(
            f"/rest/api/2/issue/{created['key']}",
            params={"fields": "summary", "expand": "renderedFields"},
        )
        assert resp.status_code == 200
        issue = resp.json()
        assert issue["id"] == created["id"]
        assert issue["fields"]["description"] == "描述文本"
        assert issue["fields"]["issuetype"]["id"] == "bug"
        assert issue["fields"]["project"]["key"] == "OPENTASK"
        assert issue["fields"]["status"]["name"] == "Todo"
        assert issue["renderedFields"]["description"] == "描述文本"

        # --- 更新（PUT：标题/优先级 204；labels 增删；assignee 子端点）---
        resp = await jira_client.put(
            f"/rest/api/2/issue/{created['key']}",
            json={"fields": {"summary": f"{TITLE_PREFIX}Jira线改题", "priority": {"id": "high"}}},
        )
        assert resp.status_code == 204
        assert resp.content == b""

        resp = await jira_client.put(
            f"/rest/api/2/issue/{created['key']}",
            json={"update": {"labels": [{"add": "ct-jira-add"}, {"remove": "ct-jira-wire"}]}},
        )
        assert resp.status_code == 204

        resp = await jira_client.put(
            f"/rest/api/2/issue/{created['key']}/assignee",
            json={"name": assignee_user.username},
        )
        assert resp.status_code == 204

        resp = await jira_client.get(f"/rest/api/2/issue/{created['key']}")
        fields = resp.json()["fields"]
        assert fields["summary"] == f"{TITLE_PREFIX}Jira线改题"
        assert fields["priority"]["id"] == "high"
        assert "ct-jira-add" in fields["labels"]
        assert "ct-jira-wire" not in fields["labels"]
        assert fields["assignee"]["name"] == assignee_user.username
        assert fields["assignee"]["accountId"] == str(assignee_user.id)

        # --- 状态流转（GET transitions → POST 204 → 状态生效 + timeline）---
        resp = await jira_client.get(f"/rest/api/2/issue/{created['key']}/transitions")
        assert resp.status_code == 200
        transitions = resp.json()["transitions"]
        by_id = {t["id"]: t for t in transitions}
        assert "todo" not in by_id  # 当前状态不可流转到自身
        assert "in_progress" in by_id
        assert by_id["in_progress"]["to"]["statusCategory"]["key"] == "indeterminate"

        resp = await jira_client.post(
            f"/rest/api/2/issue/{created['key']}/transitions",
            json={"transition": {"id": "in_progress"}},
        )
        assert resp.status_code == 204

        resp = await jira_client.get(f"/rest/api/2/issue/{created['key']}")
        assert resp.json()["fields"]["status"]["name"] == "In Progress"
        assert (
            resp.json()["fields"]["status"]["statusCategory"]["key"] == "indeterminate"
        )

        # 落库核验：状态变更写既有 timeline
        result = await db.execute(
            select(IssueTimeline).where(
                IssueTimeline.issue_id == created["id"],
                IssueTimeline.action_type == "status_changed",
            )
        )
        timelines = result.scalars().all()
        assert any(
            t.action_data and t.action_data.get("to") == "in_progress"
            for t in timelines
        )

        # done 后从 assignee 未完成列表消失（statusCategory 语义生效）
        resp = await jira_client.post(
            f"/rest/api/2/issue/{created['key']}/transitions",
            json={
                "transition": {"id": "done"},
                "update": {"comment": [{"add": {"body": "修复完成"}}]},
            },
        )
        assert resp.status_code == 204
        resp = await jira_client.post(
            "/rest/api/2/search",
            json={"jql": jql, "maxResults": 50, "fields": ["status"]},
        )
        assert all(
            i["key"] != created["key"] for i in resp.json()["issues"]
        ), "done 后仍出现在 statusCategory != Done 列表"

        # 流转评论落库（comment 端点可读回）
        resp = await jira_client.get(f"/rest/api/2/issue/{created['key']}/comment")
        bodies = [c["body"] for c in resp.json()["comments"]]
        assert "修复完成" in bodies

    async def test_create_minimal_fields(self, jira_client):
        """Orca create 最小载荷：project+issuetype+summary（IBt 形状）"""
        resp = await jira_client.post(
            "/rest/api/2/issue",
            json={
                "fields": {
                    "project": {"key": "OPENTASK"},
                    "issuetype": {"id": "feature"},
                    "summary": f"{TITLE_PREFIX}最小创建",
                }
            },
        )
        assert resp.status_code == 201
        assert resp.json()["key"].startswith("OPENTASK-")

    async def test_create_empty_summary_400(self, jira_client):
        resp = await jira_client.post(
            "/rest/api/2/issue",
            json={"fields": {"project": {"id": "OPENTASK"}, "summary": " "}},
        )
        assert resp.status_code == 400
        assert "summary" in resp.json()["errors"]

    async def test_get_unknown_issue_404(self, jira_client):
        resp = await jira_client.get("/rest/api/2/issue/OPENTASK-209901234")
        assert resp.status_code == 404
        assert resp.json()["errorMessages"][0].startswith("CONTRACT_TASK_NOT_FOUND")

    async def test_get_malformed_key_404(self, jira_client):
        resp = await jira_client.get("/rest/api/2/issue/NOT-A-KEY")
        assert resp.status_code == 404
        assert resp.json()["errorMessages"][0].startswith("CONTRACT_TASK_NOT_FOUND")

    async def test_transition_unknown_target_400(self, jira_client):
        created = await jira_client.post(
            "/rest/api/2/issue",
            json={"fields": {"issuetype": {"id": "bug"}, "summary": f"{TITLE_PREFIX}流转目标"}},
        )
        resp = await jira_client.post(
            f"/rest/api/2/issue/{created.json()['key']}/transitions",
            json={"transition": {"id": "no_such_status"}},
        )
        assert resp.status_code == 400
        assert "CONTRACT_STATUS_UNKNOWN" in resp.json()["errors"]["transition"]

    async def test_transition_same_status_400(self, jira_client):
        created = await jira_client.post(
            "/rest/api/2/issue",
            json={"fields": {"issuetype": {"id": "bug"}, "summary": f"{TITLE_PREFIX}自流转"}},
        )
        resp = await jira_client.post(
            f"/rest/api/2/issue/{created.json()['key']}/transitions",
            json={"transition": {"id": "todo"}},
        )
        assert resp.status_code == 400

    async def test_assignee_unknown_user_400(self, jira_client):
        created = await jira_client.post(
            "/rest/api/2/issue",
            json={"fields": {"issuetype": {"id": "bug"}, "summary": f"{TITLE_PREFIX}分配不存在"}},
        )
        resp = await jira_client.put(
            f"/rest/api/2/issue/{created.json()['key']}/assignee",
            json={"name": "no-such-user"},
        )
        assert resp.status_code == 400
        assert "assignee" in resp.json()["errors"]


# ============================================================================
# JQL 子集
# ============================================================================


class TestJqlSearch:
    async def _seed(self, db, test_user):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        a = await seed_issue(
            db, title=f"{TITLE_PREFIX}JQL甲", status="open",
            assignee_id=str(test_user.id), updated_at=now,
        )
        b = await seed_issue(
            db, title=f"{TITLE_PREFIX}JQL乙", status="in_progress",
            assignee_id=str(test_user.id), updated_at=now + timedelta(seconds=1),
        )
        c = await seed_issue(
            db, title=f"{TITLE_PREFIX}JQL丙", status="resolved",
            assignee_id=None, updated_at=now + timedelta(seconds=2),
        )
        return a, b, c

    async def test_orca_list_done_filter(self, jira_client, db, test_user):
        a, b, c = await self._seed(db, test_user)
        resp = await jira_client.post(
            "/rest/api/2/search",
            json={"jql": "statusCategory = Done ORDER BY updated DESC", "maxResults": 50},
        )
        keys = [i["key"] for i in resp.json()["issues"]]
        assert issue_code_to_key(c.issue_code) in keys
        assert issue_code_to_key(a.issue_code) not in keys

    async def test_orca_list_assigned_not_done_order_desc(
        self, jira_client, db, test_user
    ):
        a, b, c = await self._seed(db, test_user)
        resp = await jira_client.post(
            "/rest/api/2/search",
            json={
                "jql": (
                    "assignee = currentUser() AND statusCategory != Done "
                    "ORDER BY updated DESC"
                ),
                "maxResults": 50,
            },
        )
        keys = [i["key"] for i in resp.json()["issues"]]
        assert issue_code_to_key(b.issue_code) in keys  # 最近的在前
        assert keys.index(issue_code_to_key(b.issue_code)) < keys.index(
            issue_code_to_key(a.issue_code)
        )
        assert issue_code_to_key(c.issue_code) not in keys

    async def test_status_in_and_display_names(self, jira_client, db, test_user):
        a, b, c = await self._seed(db, test_user)
        resp = await jira_client.post(
            "/rest/api/2/search",
            json={"jql": 'status in ("Todo", "In Progress")', "maxResults": 50},
        )
        keys = {i["key"] for i in resp.json()["issues"]}
        assert issue_code_to_key(a.issue_code) in keys
        assert issue_code_to_key(b.issue_code) in keys
        assert issue_code_to_key(c.issue_code) not in keys

    async def test_key_lookup_and_in(self, jira_client, db, test_user):
        a, b, c = await self._seed(db, test_user)
        key_a = issue_code_to_key(a.issue_code)
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": f"key = {key_a}"}
        )
        assert [i["key"] for i in resp.json()["issues"]] == [key_a]

        key_b = issue_code_to_key(b.issue_code)
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": f"key in ({key_a}, {key_b})"}
        )
        assert {i["key"] for i in resp.json()["issues"]} == {key_a, key_b}

    async def test_summary_text_contains(self, jira_client, db, test_user):
        a, b, c = await self._seed(db, test_user)
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": 'summary ~ "JQL甲"'}
        )
        assert [i["key"] for i in resp.json()["issues"]] == [
            issue_code_to_key(a.issue_code)
        ]

    async def test_reporter_filter(self, jira_client, db, test_user):
        """API 创建的任务 reporter 默认落当前用户 → reporter = currentUser() 命中"""
        resp = await jira_client.post(
            "/rest/api/2/issue",
            json={"fields": {"issuetype": {"id": "bug"}, "summary": f"{TITLE_PREFIX}报告人"}},
        )
        created_key = resp.json()["key"]
        resp = await jira_client.post(
            "/rest/api/2/search",
            json={"jql": "reporter = currentUser()"},
        )
        keys = {i["key"] for i in resp.json()["issues"]}
        assert created_key in keys

    async def test_project_other_forced_empty(self, jira_client, db, test_user):
        await self._seed(db, test_user)
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": 'project = "OTHER-PROJ"'}
        )
        assert resp.json()["total"] == 0
        assert resp.json()["issues"] == []

    async def test_sprint_clause_empty(self, jira_client, db, test_user):
        await self._seed(db, test_user)
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": "sprint in openSprints()"}
        )
        assert resp.status_code == 200
        assert resp.json()["issues"] == []

    async def test_unsupported_syntax_400(self, jira_client):
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": "summary = x OR summary = y"}
        )
        assert resp.status_code == 400
        assert "jql" in resp.json()["errors"]

    async def test_unknown_status_value_400(self, jira_client):
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": 'status = "NoSuchStatus"'}
        )
        assert resp.status_code == 400
        assert "CONTRACT_STATUS_UNKNOWN" in str(resp.json())

    async def test_pagination_offset(self, jira_client, db, test_user):
        await self._seed(db, test_user)
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": "", "maxResults": 2, "startAt": 0}
        )
        page1 = resp.json()
        assert len(page1["issues"]) == 2
        assert page1["total"] >= 3
        resp = await jira_client.post(
            "/rest/api/2/search", json={"jql": "", "maxResults": 2, "startAt": 2}
        )
        assert [i["key"] for i in page1["issues"]] != [i["key"] for i in resp.json()["issues"]]


# ============================================================================
# 评论（翻页）
# ============================================================================


class TestComments:
    async def _create_issue(self, jira_client) -> str:
        resp = await jira_client.post(
            "/rest/api/2/issue",
            json={"fields": {"issuetype": {"id": "bug"}, "summary": f"{TITLE_PREFIX}评论宿主"}},
        )
        return resp.json()["key"]

    async def test_add_and_paginate(self, jira_client):
        key = await self._create_issue(jira_client)
        for i in range(3):
            resp = await jira_client.post(
                f"/rest/api/2/issue/{key}/comment", json={"body": f"评论{i}"}
            )
            assert resp.status_code == 201, resp.text
            assert resp.json()["id"]
            assert resp.json()["body"] == f"评论{i}"

        resp = await jira_client.get(
            f"/rest/api/2/issue/{key}/comment",
            params={"maxResults": 2, "startAt": 0, "orderBy": "created"},
        )
        body = resp.json()
        assert body["total"] == 3
        assert len(body["comments"]) == 2
        assert body["comments"][0]["body"] == "评论0"
        assert body["comments"][0]["author"]["name"]

        resp = await jira_client.get(
            f"/rest/api/2/issue/{key}/comment", params={"maxResults": 2, "startAt": 2}
        )
        assert len(resp.json()["comments"]) == 1

    async def test_empty_body_400(self, jira_client):
        key = await self._create_issue(jira_client)
        resp = await jira_client.post(
            f"/rest/api/2/issue/{key}/comment", json={"body": "  "}
        )
        assert resp.status_code == 400


# ============================================================================
# 元数据端点
# ============================================================================


class TestMetadata:
    async def test_project(self, jira_client):
        resp = await jira_client.get("/rest/api/2/project")
        assert resp.status_code == 200
        projects = resp.json()
        assert projects[0]["key"] == "OPENTASK"
        assert projects[0]["id"]

    async def test_priority(self, jira_client):
        resp = await jira_client.get("/rest/api/2/priority")
        ids = {p["id"] for p in resp.json()}
        assert ids == {"low", "medium", "high", "critical"}
        assert all(p["name"] for p in resp.json())

    async def test_createmeta_types(self, jira_client):
        resp = await jira_client.get(
            "/rest/api/2/issue/createmeta/OPENTASK/issuetypes",
            params={"maxResults": 50, "startAt": 0},
        )
        body = resp.json()
        assert body["total"] == len(body["values"]) >= 6
        assert "bug" in {t["id"] for t in body["values"]}

    async def test_createmeta_fields(self, jira_client):
        resp = await jira_client.get(
            "/rest/api/2/issue/createmeta/OPENTASK/issuetypes/bug",
            params={"maxResults": 100, "startAt": 0},
        )
        values = resp.json()["values"]
        by_key = {f["key"]: f for f in values}
        assert by_key["summary"]["required"] is True
        assert by_key["priority"]["allowedValues"][0]["id"] == "low"

    async def test_createmeta_unknown_type_404(self, jira_client):
        resp = await jira_client.get(
            "/rest/api/2/issue/createmeta/OPENTASK/issuetypes/nope"
        )
        assert resp.status_code == 404

    async def test_field_empty(self, jira_client):
        resp = await jira_client.get("/rest/api/2/field")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_user_search(self, jira_client, test_user):
        resp = await jira_client.get(
            "/rest/api/2/user/assignable/search",
            params={"username": ".", "maxResults": 50},
        )
        assert resp.status_code == 200
        names = {u["name"] for u in resp.json()}
        assert test_user.username in names

    async def test_myself_shape(self, jira_client, test_user):
        resp = await jira_client.get("/rest/api/2/myself")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == test_user.username
        assert "accountId" not in body  # server 模式以 name/key 为主


# ============================================================================
# 禁操作联动（contract.forbidden_operations 对 Jira 线同样生效）
# ============================================================================


class TestForbiddenOperations:
    async def test_forbidden_create_403(self, jira_client, monkeypatch):
        from opentask.api.tasks import mapping as contract_mapping

        monkeypatch.setattr(
            contract_mapping,
            "get_contract_mapping",
            lambda: contract_mapping.ContractMapping(
                issue_to_generic=dict(contract_mapping.DEFAULT_ISSUE_STATUS_TO_GENERIC),
                generic_to_issue=dict(contract_mapping.DEFAULT_GENERIC_STATUS_TO_ISSUE),
                default_issue_type="feature",
                source="default",
                forbidden_operations=frozenset({"create_task"}),
            ),
        )
        resp = await jira_client.post(
            "/rest/api/2/issue",
            json={"fields": {"issuetype": {"id": "bug"}, "summary": f"{TITLE_PREFIX}禁操作"}},
        )
        assert resp.status_code == 403
        assert "CONTRACT_FORBIDDEN" in resp.json()["errorMessages"][0]
