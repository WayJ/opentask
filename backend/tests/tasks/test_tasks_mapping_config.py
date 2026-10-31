"""状态映射配置化用例（S5 验收 S1：改配置生效 + 删配置回默认 + 非法拒绝）

配置经 mapping_config fixture 注入（stub 掉 yaml 文件读取，其余链路真实）：
loader → 结构校验 → 规范逆推导 → 缓存；另含对仓库自带 yaml 的真读校验。
"""

from datetime import datetime

import pytest
from sqlalchemy import select

from opentask.api.tasks import mapping as contract_mapping
from opentask.api.tasks.mapping import (
    DEFAULT_ISSUE_STATUS_TO_GENERIC,
    StatusMappingConfigError,
    get_contract_mapping,
    get_default_issue_type,
    get_generic_statuses,
    generic_status_to_issue,
    issue_status_to_generic,
)

from .conftest import TITLE_PREFIX, seed_issue
from opentask.models.issue.model import Issue

# 自定义映射①：closed→cancelled（默认 done）、in_progress/feedback 互换
#   词表仍为默认 5 态，但指向不同 IssueStatus —— 验证「改配置生效」
CUSTOM_MAPPING = {
    "open": "todo",
    "in_progress": "in_review",
    "feedback": "in_progress",
    "resolved": "done",
    "closed": "cancelled",
    "rejected": "cancelled",
}

# 自定义映射②：feedback 归 todo（无 in_review）—— 词表缺省 5 态少一个，
#   用于验证查询/写入按生效词表拒绝默认词表内的值
CUSTOM_MAPPING_NO_REVIEW = {
    "open": "todo",
    "in_progress": "in_progress",
    "feedback": "todo",
    "resolved": "done",
    "closed": "done",
    "rejected": "cancelled",
}


def _assert_roundtrip_identity() -> None:
    """generic → issue → generic 对生效词表全部状态恒等"""
    for generic in get_generic_statuses():
        assert issue_status_to_generic(generic_status_to_issue(generic)) == generic


# ============================================================================
# 单元：配置读取/校验/回退
# ============================================================================


class TestMappingConfigUnit:
    def test_custom_config_takes_effect(self, mapping_config):
        """改配置生效：双向表按配置走，source=config，往返恒等"""
        mapping_config({"contract": {"status_mapping": CUSTOM_MAPPING}})

        mapping = get_contract_mapping()
        assert mapping.source == "config"
        # 正向按配置：closed → cancelled（默认是 done）
        assert issue_status_to_generic("closed") == "cancelled"
        assert issue_status_to_generic("in_progress") == "in_review"
        # 逆向取规范逆：cancelled ← closed/rejected，枚举序 closed 在前 → closed
        assert generic_status_to_issue("cancelled") == "closed"
        assert generic_status_to_issue("in_review") == "in_progress"
        assert generic_status_to_issue("in_progress") == "feedback"
        # 词表 = 配置 value 集
        assert get_generic_statuses() == frozenset(CUSTOM_MAPPING.values())
        _assert_roundtrip_identity()

    def test_custom_mapping_reverse_independent_of_key_order(self, mapping_config):
        """规范逆与 yaml key 顺序无关：done ← resolved/closed 恒取 resolved"""
        reordered = {k: CUSTOM_MAPPING[k] for k in reversed(list(CUSTOM_MAPPING))}
        mapping_config({"contract": {"status_mapping": reordered}})
        assert generic_status_to_issue("done") == "resolved"
        assert generic_status_to_issue("cancelled") == "closed"

    def test_remove_config_falls_back_to_default(self, mapping_config):
        """删配置回默认：source=default，双向表与代码默认表一致"""
        mapping_config(None)

        mapping = get_contract_mapping()
        assert mapping.source == "default"
        assert mapping.issue_to_generic == DEFAULT_ISSUE_STATUS_TO_GENERIC
        assert issue_status_to_generic("closed") == "done"
        assert generic_status_to_issue("done") == "resolved"
        assert generic_status_to_issue("cancelled") == "rejected"
        assert get_generic_statuses() == frozenset(
            DEFAULT_ISSUE_STATUS_TO_GENERIC.values()
        )
        _assert_roundtrip_identity()

    def test_partial_config_rejected(self, mapping_config):
        """缺 IssueStatus 覆盖 → 快速失败（拒绝静默降级到半套映射）"""
        partial = {k: v for k, v in DEFAULT_ISSUE_STATUS_TO_GENERIC.items()
                   if k != "closed"}
        mapping_config({"contract": {"status_mapping": partial}})
        with pytest.raises(StatusMappingConfigError, match="closed"):
            get_contract_mapping()

    def test_unknown_status_key_rejected(self, mapping_config):
        bogus = dict(DEFAULT_ISSUE_STATUS_TO_GENERIC, bogus="todo")
        mapping_config({"contract": {"status_mapping": bogus}})
        with pytest.raises(StatusMappingConfigError, match="未知 IssueStatus"):
            get_contract_mapping()

    def test_non_string_value_rejected(self, mapping_config):
        bogus = dict(DEFAULT_ISSUE_STATUS_TO_GENERIC, open=123)
        mapping_config({"contract": {"status_mapping": bogus}})
        with pytest.raises(StatusMappingConfigError, match="open"):
            get_contract_mapping()

    def test_default_issue_type_configurable(self, mapping_config):
        mapping_config(
            {"contract": {"status_mapping": CUSTOM_MAPPING,
                          "default_issue_type": "bug"}}
        )
        assert get_default_issue_type() == "bug"

        mapping_config(None)
        assert get_default_issue_type() == "feature"

    def test_shipped_yaml_contract_section_valid(self):
        """仓库自带 config/default.yaml 的 contract 段真实加载且合法（doc_sync 守护）"""
        contract_mapping.reset_contract_mapping_cache()
        try:
            mapping = get_contract_mapping()
            assert mapping.source == "config"  # default.yaml 随仓库携带该段
            assert mapping.issue_to_generic == DEFAULT_ISSUE_STATUS_TO_GENERIC
            assert get_default_issue_type() == "feature"
            _assert_roundtrip_identity()
        finally:
            contract_mapping.reset_contract_mapping_cache()


# ============================================================================
# HTTP：配置驱动的读写映射（Orca → OpenTask → Orca 往返）
# ============================================================================


@pytest.mark.asyncio
class TestMappingConfigHttp:
    async def test_custom_mapping_roundtrip_over_http(
        self, client, db, assignee_user, mapping_config
    ):
        """改配置生效（HTTP 全链路）：closed→cancelled 读出；写入按规范逆落 closed"""
        mapping_config({"contract": {"status_mapping": CUSTOM_MAPPING}})

        # 读向：种子 closed → 契约侧 cancelled（默认表下是 done）
        seeded = await seed_issue(
            db,
            title=f"{TITLE_PREFIX}映射读",
            status="closed",
            assignee_id=str(assignee_user.id),
            updated_at=datetime(2026, 3, 1, 8, 0, 0),
        )
        resp = await client.get(f"/tasks/{seeded.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        # 写向：POST cancelled → 落库 closed（配置的规范逆；默认表下是 rejected）
        resp = await client.post(
            "/tasks",
            json={
                "title": f"{TITLE_PREFIX}映射写",
                "status": "cancelled",
                "assignee": str(assignee_user.id),
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "cancelled"
        created_id = resp.json()["id"]
        issue_row = (
            await db.execute(select(Issue).where(Issue.id == created_id))
        ).scalar_one()
        assert issue_row.status == "closed"

        # PATCH in_review → 落库 in_progress（配置互换；默认表下是 feedback）
        resp = await client.patch(
            f"/tasks/{created_id}", json={"status": "in_review"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "in_review"
        # 请求侧会话已提交；本地会话身份映射持旧对象，过期后重查取新值
        # （id 先落局部变量——expire_all 后访问实例属性会同步懒加载，async 下报 MissingGreenlet）
        db.expire_all()
        issue_row = (
            await db.execute(select(Issue).where(Issue.id == created_id))
        ).scalar_one()
        assert issue_row.status == "in_progress"

    async def test_default_mapping_after_config_removed(
        self, client, db, assignee_user, mapping_config
    ):
        """删配置回默认（HTTP 全链路）：closed→done、cancelled 写入落 rejected"""
        mapping_config(None)

        seeded = await seed_issue(
            db,
            title=f"{TITLE_PREFIX}默认读",
            status="closed",
            assignee_id=str(assignee_user.id),
            updated_at=__import__("datetime").datetime(2026, 3, 1, 9, 0, 0),
        )
        resp = await client.get(f"/tasks/{seeded.id}")
        assert resp.json()["status"] == "done"

        resp = await client.post(
            "/tasks",
            json={"title": f"{TITLE_PREFIX}默认写", "status": "cancelled"},
        )
        issue_row = (
            await db.execute(select(Issue).where(Issue.id == resp.json()["id"]))
        ).scalar_one()
        assert issue_row.status == "rejected"

    async def test_vocabulary_follows_config_422(
        self, client, mapping_config
    ):
        """生效词表拒绝默认词表内、配置外的状态（查询与写入均 422）"""
        mapping_config(
            {"contract": {"status_mapping": CUSTOM_MAPPING_NO_REVIEW}}
        )

        resp = await client.get("/tasks", params={"status": "in_review"})
        assert resp.status_code == 422

        resp = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}词表", "status": "in_review"}
        )
        assert resp.status_code == 422

        # 配置内状态正常
        resp = await client.get("/tasks", params={"status": "todo"})
        assert resp.status_code == 200

    async def test_default_issue_type_over_http(self, client, db, mapping_config):
        """contract.default_issue_type 生效：POST 落库 type 按配置"""
        mapping_config(
            {"contract": {"status_mapping": CUSTOM_MAPPING,
                          "default_issue_type": "bug"}}
        )
        resp = await client.post("/tasks", json={"title": f"{TITLE_PREFIX}类型"})
        issue_row = (
            await db.execute(select(Issue).where(Issue.id == resp.json()["id"]))
        ).scalar_one()
        assert issue_row.type == "bug"
