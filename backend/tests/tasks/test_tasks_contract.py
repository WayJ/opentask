"""任务源契约 API 单元测试

覆盖（对应 sprint S4 验收场景 S1–S4）：
- CRUD 全路径：创建→读取→更新→软删除→软删后再读 404（S1）
- updated_since 游标边界：同游标重复拉取零重复、边界时刻排他语义（S2）
- 字段映射往返：通用模型 ↔ Issue 双向、labels↔tags、assignee+metadata.username（S3）
- PATCH 状态变更写既有 timeline（S4）
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from opentask.models.issue.enums import IssueStatus
from opentask.models.issue.model import Issue, IssueTag, IssueTimeline
from opentask.models.tag.model import Tag

from opentask.api.tasks.converters import issue_to_contract_task
from opentask.api.tasks.mapping import (
    DEFAULT_ISSUE_STATUS_TO_GENERIC,
    build_issue_url,
    generic_status_to_issue,
    get_generic_statuses,
    issue_status_to_generic,
    normalize_updated_since,
)

from .conftest import TITLE_PREFIX, seed_issue

# ============================================================================
# S3: 字段映射（纯单元，无 HTTP）
# ============================================================================


class TestStatusMapping:
    """状态映射表（生效配置=随仓库默认表）：往返恒等 + 全函数

    配置化覆盖（改配置生效/删配置回默认/非法配置拒绝）见
    test_tasks_mapping_config.py。
    """

    def test_generic_roundtrip_identity(self):
        """generic → issue → generic 对全部通用状态恒等（DoD 往返要求）"""
        for generic in get_generic_statuses():
            assert issue_status_to_generic(generic_status_to_issue(generic)) == generic

    def test_issue_to_generic_total(self):
        """全部 6 种 IssueStatus 均可映射（无遗漏）"""
        for status in IssueStatus:
            assert issue_status_to_generic(status.value) in get_generic_statuses()

    def test_default_table_shape(self):
        """默认表形状：done 为 resolved/closed 的共同归宿，规范逆取 resolved"""
        assert DEFAULT_ISSUE_STATUS_TO_GENERIC["resolved"] == "done"
        assert DEFAULT_ISSUE_STATUS_TO_GENERIC["closed"] == "done"
        assert generic_status_to_issue("done") == "resolved"

    def test_unknown_generic_status_rejected(self):
        with pytest.raises(ValueError):
            generic_status_to_issue("bogus")


class TestFieldMapping:
    def test_normalize_updated_since_tz_aware_to_naive_utc(self):
        aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=8)))
        assert normalize_updated_since(aware) == datetime(2026, 1, 1, 4, 0, 0)

    def test_normalize_updated_since_naive_passthrough(self):
        naive = datetime(2026, 1, 1, 4, 0, 0)
        assert normalize_updated_since(naive) == naive

    def test_build_issue_url(self):
        assert build_issue_url("abc") == "/issue/detail?id=abc"

    def test_issue_to_contract_task_mapping(self):
        """通用模型字段（id/title/description/status/assignee/url/timestamps+metadata）
        与 Issue 双向转换无丢失；labels↔tags、assignee+metadata.username 正确"""
        issue = Issue(
            id=str(uuid.uuid4()),
            issue_code="ISSUE2026-77",
            title="映射往返",
            description="描述内容",
            type="feature",
            status="in_progress",
            priority="high",
            assignee_id="user-123",
            reporter_id="user-reporter",
            created_at=datetime(2026, 1, 1, 8, 0, 0),
            updated_at=datetime(2026, 1, 2, 9, 30, 0),
        )
        issue.tags = [IssueTag(issue_id=issue.id, tag_id=1), IssueTag(issue_id=issue.id, tag_id=2)]

        task = issue_to_contract_task(
            issue,
            tag_names_by_id={1: "beta", 2: "alpha"},
            usernames_by_id={"user-123": "user-123-name"},
        )

        assert task.id == issue.id
        assert task.title == "映射往返"
        assert task.description == "描述内容"
        assert task.status == "in_progress"
        assert task.assignee == "user-123"
        assert task.url == f"/issue/detail?id={issue.id}"
        assert task.created_at == datetime(2026, 1, 1, 8, 0, 0)
        assert task.updated_at == datetime(2026, 1, 2, 9, 30, 0)
        assert task.labels == ["alpha", "beta"]
        assert task.metadata["issue_code"] == "ISSUE2026-77"
        assert task.metadata["type"] == "feature"
        assert task.metadata["priority"] == "high"
        assert task.metadata["reporter_id"] == "user-reporter"
        assert task.metadata["username"] == "user-123-name"


# ============================================================================
# S1: CRUD 全路径（HTTP）
# ============================================================================


@pytest.mark.asyncio
class TestContractCrud:
    async def test_create_task_full_persistence(self, client, db, test_user, assignee_user):
        """POST 完整落库：title/description/assignee/status/labels 经 issue service"""
        resp = await client.post(
            "/tasks",
            json={
                "title": f"{TITLE_PREFIX}契约创建",
                "description": "契约层创建的描述",
                "status": "in_progress",
                "assignee": str(assignee_user.id),
                "labels": ["ct-backend", "ct-orca"],
            },
        )
        assert resp.status_code == 201, resp.text
        task = resp.json()

        # 响应形状（通用任务模型）
        assert task["title"] == f"{TITLE_PREFIX}契约创建"
        assert task["description"] == "契约层创建的描述"
        assert task["status"] == "in_progress"
        assert task["assignee"] == str(assignee_user.id)
        assert set(task["labels"]) == {"ct-backend", "ct-orca"}
        assert task["url"] == f"/issue/detail?id={task['id']}"
        assert task["created_at"] and task["updated_at"]
        # D12：assignee 字符串 ID + metadata.username
        assert task["metadata"]["username"] == assignee_user.username
        assert task["metadata"]["issue_code"].startswith("ISSUE")

        # 落库断言（Issue 行 + 标签关联 + created timeline）
        issue_row = (
            await db.execute(select(Issue).where(Issue.id == task["id"]))
        ).scalar_one()
        assert issue_row.title == f"{TITLE_PREFIX}契约创建"
        assert issue_row.status == "in_progress"
        assert issue_row.type == "feature"
        assert issue_row.assignee_id == str(assignee_user.id)
        assert issue_row.reporter_id == str(test_user.id)
        assert issue_row.is_deleted is False

        label_names = {
            n
            for (n,) in await db.execute(
                select(Tag.name)
                .join(IssueTag, IssueTag.tag_id == Tag.id)
                .where(IssueTag.issue_id == task["id"])
            )
        }
        assert label_names == {"ct-backend", "ct-orca"}

        actions = [
            a
            for (a,) in await db.execute(
                select(IssueTimeline.action_type).where(
                    IssueTimeline.issue_id == task["id"]
                )
            )
        ]
        assert "created" in actions

    async def test_create_task_defaults(self, client, db, test_user):
        """POST 最小载荷：status 默认 todo→open，assignee/labels 可空"""
        resp = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}默认值"}
        )
        assert resp.status_code == 201, resp.text
        task = resp.json()
        assert task["status"] == "todo"
        assert task["assignee"] is None
        assert task["labels"] == []
        assert "username" not in task["metadata"]

        issue_row = (
            await db.execute(select(Issue).where(Issue.id == task["id"]))
        ).scalar_one()
        assert issue_row.status == "open"

    async def test_get_task_by_id(self, client, test_user, assignee_user):
        created = (
            await client.post(
                "/tasks",
                json={
                    "title": f"{TITLE_PREFIX}读取",
                    "assignee": str(assignee_user.id),
                    "labels": ["ct-read"],
                },
            )
        ).json()

        resp = await client.get(f"/tasks/{created['id']}")
        assert resp.status_code == 200
        task = resp.json()
        assert task["id"] == created["id"]
        assert task["assignee"] == str(assignee_user.id)
        assert task["metadata"]["username"] == assignee_user.username
        assert task["labels"] == ["ct-read"]

    async def test_get_task_not_found(self, client):
        resp = await client.get(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_list_tasks_filter_and_pagination(self, client, db, assignee_user):
        """过滤 status/assignee + 分页 limit/offset + 排序确定性"""
        base = datetime(2026, 1, 10, 8, 0, 0)
        seed_specs = [
            ("open", base + timedelta(hours=1)),
            ("in_progress", base + timedelta(hours=2)),
            ("resolved", base + timedelta(hours=3)),
            ("closed", base + timedelta(hours=4)),
            ("rejected", base + timedelta(hours=5)),
        ]
        for status, ts in seed_specs:
            await seed_issue(
                db,
                title=f"{TITLE_PREFIX}列表-{status}",
                status=status,
                assignee_id=str(assignee_user.id),
                updated_at=ts,
            )

        # assignee 过滤：只看种子数据
        resp = await client.get(
            "/tasks", params={"assignee": str(assignee_user.id), "limit": 100}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 5
        # 排序确定性：updated_at 升序
        times = [i["updated_at"] for i in body["items"]]
        assert times == sorted(times)
        # 状态前向映射（6→5）：resolved/closed 均显示为 done
        statuses = {i["status"] for i in body["items"]}
        assert statuses == {"todo", "in_progress", "done", "cancelled"}
        assert sorted(i["status"] for i in body["items"] if i["status"] == "done") == [
            "done",
            "done",
        ]

        # status 过滤：todo 只剩 open 那条
        resp = await client.get(
            "/tasks",
            params={"assignee": str(assignee_user.id), "status": "todo"},
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "todo"

        # 分页：limit=2 三页取完，页间无重叠
        seen: list[str] = []
        for offset in (0, 2, 4):
            resp = await client.get(
                "/tasks",
                params={
                    "assignee": str(assignee_user.id),
                    "limit": 2,
                    "offset": offset,
                },
            )
            body = resp.json()
            assert body["total"] == 5
            assert body["limit"] == 2 and body["offset"] == offset
            seen.extend(i["id"] for i in body["items"])
        assert len(seen) == 5 and len(set(seen)) == 5

    async def test_patch_task_fields_and_status_writes_timeline(
        self, client, db, test_user
    ):
        """PATCH 更新字段；状态变更写既有 timeline（S4）"""
        created = (
            await client.post("/tasks", json={"title": f"{TITLE_PREFIX}更新"})
        ).json()

        resp = await client.patch(
            f"/tasks/{created['id']}",
            json={"title": f"{TITLE_PREFIX}更新后", "status": "done"},
        )
        assert resp.status_code == 200, resp.text
        task = resp.json()
        assert task["title"] == f"{TITLE_PREFIX}更新后"
        assert task["status"] == "done"

        # 落库：generic done → issue resolved
        issue_row = (
            await db.execute(select(Issue).where(Issue.id == created["id"]))
        ).scalar_one()
        assert issue_row.status == "resolved"

        # timeline：status_changed 记录 from open → to resolved
        status_events = [
            (a, d)
            for (a, d) in await db.execute(
                select(IssueTimeline.action_type, IssueTimeline.action_data).where(
                    IssueTimeline.issue_id == created["id"]
                )
            )
            if a == "status_changed"
        ]
        assert len(status_events) == 1
        assert status_events[0][1]["from"] == "open"
        assert status_events[0][1]["to"] == "resolved"

    async def test_patch_task_labels_replace_writes_timeline(self, client, db):
        """PATCH labels 替换语义 + label_added/label_removed timeline"""
        created = (
            await client.post(
                "/tasks",
                json={"title": f"{TITLE_PREFIX}标签", "labels": ["ct-old"]},
            )
        ).json()

        resp = await client.patch(
            f"/tasks/{created['id']}", json={"labels": ["ct-new", "ct-old"]}
        )
        assert resp.status_code == 200
        assert sorted(resp.json()["labels"]) == ["ct-new", "ct-old"]

        # 幂等替换：去掉 ct-old 后再全量重设，最终只剩 ct-new
        resp = await client.patch(
            f"/tasks/{created['id']}", json={"labels": ["ct-new"]}
        )
        assert resp.status_code == 200
        assert resp.json()["labels"] == ["ct-new"]

        names = {
            n
            for (n,) in await db.execute(
                select(Tag.name)
                .join(IssueTag, IssueTag.tag_id == Tag.id)
                .where(IssueTag.issue_id == created["id"])
            )
        }
        assert names == {"ct-new"}

        actions = [
            a
            for (a,) in await db.execute(
                select(IssueTimeline.action_type).where(
                    IssueTimeline.issue_id == created["id"]
                )
            )
        ]
        assert "label_added" in actions
        assert "label_removed" in actions

    async def test_patch_task_not_found(self, client):
        resp = await client.patch(
            f"/tasks/{uuid.uuid4()}", json={"title": "nope"}
        )
        assert resp.status_code == 404

    async def test_delete_task_soft_delete(self, client, db, assignee_user):
        """DELETE 软删除：行保留 is_deleted=True，读取 404，列表不可见（D8）"""
        created = (
            await client.post(
                "/tasks",
                json={
                    "title": f"{TITLE_PREFIX}删除",
                    "assignee": str(assignee_user.id),
                },
            )
        ).json()

        resp = await client.delete(f"/tasks/{created['id']}")
        assert resp.status_code == 204

        # 再读 404（软删语义）
        resp = await client.get(f"/tasks/{created['id']}")
        assert resp.status_code == 404

        # 列表不可见
        resp = await client.get(
            "/tasks", params={"assignee": str(assignee_user.id)}
        )
        assert resp.json()["total"] == 0

        # 物理行仍在，is_deleted=True
        issue_row = (
            await db.execute(select(Issue).where(Issue.id == created["id"]))
        ).scalar_one()
        assert issue_row.is_deleted is True

        # 软删的任务 updated_at 变化 → 游标能感知删除（供消费方对账）
        resp = await client.get(
            "/tasks",
            params={
                "assignee": str(assignee_user.id),
                "updated_since": issue_row.updated_at.isoformat(),
            },
        )
        assert resp.json()["total"] == 0

    async def test_delete_task_not_found(self, client):
        resp = await client.delete(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404


# ============================================================================
# S2: updated_since 增量游标边界
# ============================================================================


@pytest.mark.asyncio
class TestUpdatedSinceCursor:
    async def test_cursor_exclusive_boundary_semantics(self, client, db, assignee_user):
        """边界时刻语义：恰好等于游标的记录 **不含**（严格大于），
        一微秒前的游标则含它 —— 语义有显式断言"""
        t1 = datetime(2026, 2, 1, 8, 0, 0)
        t2 = datetime(2026, 2, 1, 9, 0, 0)
        t3 = datetime(2026, 2, 1, 10, 0, 0)
        for ts in (t1, t2, t3):
            await seed_issue(
                db,
                title=f"{TITLE_PREFIX}游标-{ts.hour}",
                assignee_id=str(assignee_user.id),
                updated_at=ts,
            )

        params = {"assignee": str(assignee_user.id)}

        # updated_since = t1：t1 排他，得 t2/t3
        resp = await client.get(
            "/tasks", params={**params, "updated_since": t1.isoformat()}
        )
        body = resp.json()
        assert body["total"] == 2
        hours = {i["title"].split("-")[-1] for i in body["items"]}
        assert hours == {"9", "10"}

        # updated_since = t1 - 1µs：t1 严格大于游标，得全部
        just_before = (t1 - timedelta(microseconds=1)).isoformat()
        resp = await client.get(
            "/tasks", params={**params, "updated_since": just_before}
        )
        assert resp.json()["total"] == 3

        # updated_since = t3（最新时刻）：空集
        resp = await client.get(
            "/tasks", params={**params, "updated_since": t3.isoformat()}
        )
        assert resp.json()["total"] == 0

    async def test_same_cursor_repeat_pull_zero_duplicates(
        self, client, db, assignee_user
    ):
        """同游标重复拉取：两次结果一致且并集零重复（D10/DoD）"""
        base = datetime(2026, 2, 2, 8, 0, 0)
        # 种子时刻全部严格大于游标 base（排他语义下才应全量返回）
        for i in range(1, 5):
            await seed_issue(
                db,
                title=f"{TITLE_PREFIX}重复-{i}",
                assignee_id=str(assignee_user.id),
                updated_at=base + timedelta(minutes=i),
            )
        cursor = base.isoformat()
        params = {"assignee": str(assignee_user.id), "updated_since": cursor}

        first = (await client.get("/tasks", params=params)).json()
        second = (await client.get("/tasks", params=params)).json()

        assert first["total"] == second["total"] == 4
        ids_first = [i["id"] for i in first["items"]]
        ids_second = [i["id"] for i in second["items"]]
        assert ids_first == ids_second

        # 零重复语义①：返回集内无重复 id
        assert len(set(ids_first)) == 4

        # 零重复语义②：同一游标下翻页（limit/offset），跨页并集无重复且与整拉一致
        paged: list[str] = []
        for offset in (0, 2):
            page = (
                await client.get(
                    "/tasks", params={**params, "limit": 2, "offset": offset}
                )
            ).json()
            paged.extend(i["id"] for i in page["items"])
        assert len(paged) == len(set(paged)) == 4
        assert set(paged) == set(ids_first)

        # 零重复语义③：所有返回项 updated_at 严格大于游标（≤游标的绝不回流）
        assert all(i["updated_at"] > cursor for i in first["items"])

        # 游标推进：以返回集最大 updated_at 为新游标，拉到的与已有零重叠
        max_updated = max(i["updated_at"] for i in first["items"])
        third = (
            await client.get(
                "/tasks", params={**params, "updated_since": max_updated}
            )
        ).json()
        ids_third = [i["id"] for i in third["items"]]
        assert not (set(ids_first) & set(ids_third))

    async def test_cursor_sees_updates(self, client, db, assignee_user):
        """游标增量：PATCH 触碰 updated_at 后，旧游标能拉到该任务"""
        t_old = datetime(2026, 2, 3, 8, 0, 0)
        await seed_issue(
            db,
            title=f"{TITLE_PREFIX}增量",
            assignee_id=str(assignee_user.id),
            updated_at=t_old,
        )

        # 以 t_old 之后、现在之前为游标：暂时拉不到
        before_patch = datetime.utcnow() - timedelta(seconds=1)
        resp = await client.get(
            "/tasks",
            params={
                "assignee": str(assignee_user.id),
                "updated_since": before_patch.isoformat(),
            },
        )
        assert resp.json()["total"] == 0

        items = (
            await client.get(
                "/tasks", params={"assignee": str(assignee_user.id), "limit": 1}
            )
        ).json()["items"]
        task_id = items[0]["id"]

        resp = await client.patch(f"/tasks/{task_id}", json={"title": f"{TITLE_PREFIX}增量改"})
        assert resp.status_code == 200

        resp = await client.get(
            "/tasks",
            params={
                "assignee": str(assignee_user.id),
                "updated_since": before_patch.isoformat(),
            },
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == task_id
        assert body["items"][0]["title"] == f"{TITLE_PREFIX}增量改"


# ============================================================================
# 契约校验（schema 违规 → 422）
# ============================================================================


@pytest.mark.asyncio
class TestContractValidation:
    async def test_create_unknown_status_422(self, client):
        resp = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}坏状态", "status": "bogus"}
        )
        assert resp.status_code == 422

    async def test_list_unknown_status_422(self, client):
        resp = await client.get("/tasks", params={"status": "bogus"})
        assert resp.status_code == 422

    async def test_create_empty_title_422(self, client):
        resp = await client.post("/tasks", json={"title": ""})
        assert resp.status_code == 422

    async def test_patch_unknown_status_422(self, client):
        created = (
            await client.post("/tasks", json={"title": f"{TITLE_PREFIX}校验"})
        ).json()
        resp = await client.patch(
            f"/tasks/{created['id']}", json={"status": "bogus"}
        )
        assert resp.status_code == 422
