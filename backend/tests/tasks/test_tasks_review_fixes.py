"""Code review 回归用例（协调者 7 项发现，S6 批次修复）

编号即协调者消息序号；1-4 按 review 要求带测试断言，5-7 各配可行验证：
1. GET /tasks?status=<generic> 按正映射集合过滤（done → resolved+closed，
   单值逆映射会漏 closed）
2. POST /tasks 无 status 时默认值自生效配置推导（词表可合法省略 todo，
   硬编码 "todo" 会 500）
3. contract.default_issue_type 对照 IssueType 词表校验（非法快速失败）
4. client_credentials 交换显式无限制 scope：must_change_password 用户
   换到的 JWT 无 scp，不再被折叠成误导性 401 INVALID
5. 交换不落 refresh_tokens 孤儿行（RFC 6749 §4.4.3 不下发 refresh）
6. sync_issue_labels 收集后单次提交（标签创建不再循环内逐个 commit）
7. create_issue 并发撞 issue_code 唯一索引重试；编号生成容忍非数字后缀
"""

from datetime import datetime

import pytest
from sqlalchemy import func, select, update

from opentask.api.tasks.mapping import (
    ContractConfigError,
    get_contract_mapping,
    get_default_issue_type,
)
from opentask.api.tasks.service import (
    ContractIssueService,
    get_issue_current_tags,
    sync_issue_labels,
)
from opentask.models.issue.model import Issue
from opentask.models.issue.schema import IssueCreate
from opentask.models.user_center.model import RefreshToken
from opentask.services.issue_service import IssueService

from .conftest import LABEL_PREFIX, TITLE_PREFIX, create_api_key, seed_issue


# ============================================================================
# 1. 状态过滤按正映射集合（done → resolved + closed）
# ============================================================================


@pytest.mark.asyncio
class TestStatusFilterMatchesForwardSet:
    async def test_done_filter_includes_all_mapped_issue_statuses(
        self, client, db
    ):
        """?status=done 命中 resolved 与 closed 两者（正向展示口径一致）"""
        base = datetime(2026, 2, 1, 8, 0, 0)
        resolved = await seed_issue(
            db, title=f"{TITLE_PREFIX}done-resolved", status="resolved",
            updated_at=base,
        )
        closed = await seed_issue(
            db, title=f"{TITLE_PREFIX}done-closed", status="closed",
            updated_at=base,
        )
        open_issue = await seed_issue(
            db, title=f"{TITLE_PREFIX}done-open", status="open",
            updated_at=base,
        )

        body = (await client.get("/tasks", params={"status": "done"})).json()
        ids = {t["id"] for t in body["items"]}
        assert str(resolved.id) in ids, "done 过滤应命中 resolved"
        assert str(closed.id) in ids, "done 过滤应同时命中 closed（正映射集合）"
        assert str(open_issue.id) not in ids
        assert {t["status"] for t in body["items"]} == {"done"}


# ============================================================================
# 2. POST 无 status：默认值自生效配置推导
# ============================================================================


@pytest.mark.asyncio
class TestDefaultStatusFromConfig:
    async def test_post_without_status_defaults_to_todo(self, client):
        """默认词表：缺省 status → todo"""
        resp = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}默认todo"}
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "todo"

    async def test_post_without_status_when_todo_absent_from_vocabulary(
        self, client, mapping_config
    ):
        """词表合法省略 todo：缺省取规范序首个（open 的正映射），不 500"""
        mapping_config(
            {
                "contract": {
                    "status_mapping": {
                        "open": "backlog",
                        "in_progress": "wip",
                        "feedback": "review",
                        "resolved": "shipped",
                        "closed": "shipped",
                        "rejected": "dropped",
                    }
                }
            }
        )
        resp = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}无todo词表默认"}
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "backlog"


# ============================================================================
# 3. default_issue_type 对照 IssueType 词表校验
# ============================================================================


class TestDefaultIssueTypeValidation:
    def test_unknown_issue_type_fails_fast(self, mapping_config):
        mapping_config({"contract": {"default_issue_type": "story"}})
        with pytest.raises(ContractConfigError, match="story"):
            get_contract_mapping()

    def test_valid_custom_issue_type(self, mapping_config):
        mapping_config({"contract": {"default_issue_type": "incident"}})
        assert get_default_issue_type() == "incident"


# ============================================================================
# 4. client_credentials 交换显式无限制 scope（must_change_password 不降权）
# ============================================================================


@pytest.mark.asyncio
class TestExchangeScopeForMustChangePasswordUser:
    async def test_exchanged_jwt_has_unrestricted_scope(
        self, raw_client, db, test_user
    ):
        """must_change_password 用户换到的 JWT 无 scp：访问契约端点 200

        旧行为：issue_tokens 未显式传 scope → 继承 scp=pwd_change →
        契约端点 403 被误折叠成 401 CONTRACT_AUTH_INVALID。
        """
        test_user.must_change_password = True
        await db.commit()

        key = await create_api_key(db, test_user, name="ct-pwdchg")
        resp = await raw_client.post(
            "/tasks/token",
            data={"grant_type": "client_credentials", "client_secret": key},
        )
        assert resp.status_code == 200, resp.text
        jwt_token = resp.json()["access_token"]

        resp = await raw_client.get(
            "/tasks", headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert resp.status_code == 200, resp.text
        assert "items" in resp.json()


# ============================================================================
# 5. 交换不落 refresh_tokens 孤儿行
# ============================================================================


@pytest.mark.asyncio
class TestExchangeNoRefreshRows:
    async def test_exchange_does_not_persist_refresh_token(
        self, raw_client, db, test_user
    ):
        user_id = str(test_user.id)

        async def count_refresh_rows() -> int:
            result = await db.execute(
                select(func.count())
                .select_from(RefreshToken)
                .where(RefreshToken.user_id == user_id)
            )
            return result.scalar()

        before = await count_refresh_rows()
        key = await create_api_key(db, test_user, name="ct-norefresh")
        resp = await raw_client.post(
            "/tasks/token",
            data={"grant_type": "client_credentials", "client_secret": key},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "refresh_token" not in body  # 不下发
        assert await count_refresh_rows() == before  # 也不落库（无孤儿行）


# ============================================================================
# 6. sync_issue_labels 收集后单次提交
# ============================================================================


@pytest.mark.asyncio
class TestLabelSyncSingleCommit:
    async def test_sync_labels_with_new_tags_commits_once(
        self, db, test_user, monkeypatch
    ):
        """新建 3 个标签的同步过程只提交一次（原子性：不再循环内逐个 commit）"""
        issue = await seed_issue(
            db, title=f"{TITLE_PREFIX}单次提交", updated_at=datetime(2026, 2, 2, 9, 0, 0)
        )
        service = ContractIssueService(db)

        commits: list[int] = []
        original_commit = db.commit

        async def spy_commit() -> None:
            commits.append(1)
            await original_commit()

        monkeypatch.setattr(db, "commit", spy_commit)

        labels = [f"{LABEL_PREFIX}one", f"{LABEL_PREFIX}two", f"{LABEL_PREFIX}three"]
        await sync_issue_labels(service, issue.id, labels, str(test_user.id))

        assert len(commits) == 1, "标签同步应收集后单次提交"
        current = await get_issue_current_tags(db, issue.id)
        assert set(current) == set(labels)


# ============================================================================
# 7. issue_code 并发撞号重试 + 非数字后缀容忍
# ============================================================================


@pytest.mark.asyncio
class TestIssueCodeCollisionRetry:
    async def test_create_retries_on_unique_collision(
        self, db, test_user, monkeypatch
    ):
        """并发窗口算出重复编号 → IntegrityError → 重算重试后成功"""
        occupied = await seed_issue(
            db, title=f"{TITLE_PREFIX}撞号占位", updated_at=datetime(2026, 2, 3, 9, 0, 0)
        )
        # 先快照字符串：重试路径的 rollback 会 expire 身份映射中的对象，
        # 事后访问 occupied 的列属性会触发异步上下文外的懒加载
        occupied_code = occupied.issue_code
        service = ContractIssueService(db)

        calls = {"n": 0}
        real_generate = IssueService._generate_issue_code

        async def collide_once(inner_self, workspace_id=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return occupied_code  # 模拟并发窗口内的同号
            return await real_generate(inner_self, workspace_id)

        monkeypatch.setattr(IssueService, "_generate_issue_code", collide_once)

        created = await service.create_issue(
            IssueCreate(title=f"{TITLE_PREFIX}撞号重试", type="feature", status="open"),
            str(test_user.id),
            dept_id=None,
        )
        assert calls["n"] == 2, "撞号后应重算重试一次"
        assert created.id is not None
        assert created.issue_code != occupied_code

    async def test_generate_code_tolerates_non_numeric_suffix(self, db):
        """历史脏数据（非数字后缀）不再让编号生成报错"""
        row = await seed_issue(
            db, title=f"{TITLE_PREFIX}非数字后缀", updated_at=datetime(2026, 2, 3, 9, 30, 0)
        )
        year = datetime.now().year
        await db.execute(
            update(Issue)
            .where(Issue.id == row.id)
            .values(issue_code=f"ISSUE{year}-MANUAL")
        )
        await db.commit()

        code = await ContractIssueService(db)._generate_issue_code()
        suffix = code[len(f"ISSUE{year}-"):]
        assert code.startswith(f"ISSUE{year}-")
        assert suffix.isdigit(), f"应给出数字序号而非报错（当前: {code!r}）"
