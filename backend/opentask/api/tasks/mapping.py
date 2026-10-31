"""字段映射层：通用任务模型 ↔ OpenTask Issue 双向转换

职责（epic ADR D7/D12 + sprint S4 D1/D2/D3）：
- 状态映射默认表：IssueStatus（open/in_progress/feedback/resolved/closed/rejected）
  ↔ 通用状态（todo/in_progress/in_review/done/cancelled）
- issue→generic 为全函数（6 → 5，resolved 与 closed 均归 done）；
  generic→issue 取规范逆（done→resolved），
  因此 generic→issue→generic 对全部通用状态保持恒等（往返无损）。
- 可配置化留待 S5（届时把下面的模块级映射表换成配置来源即可，函数签名不变）。

POST 落库经 IssueService（业务逻辑与 UI 侧一致），本模块只做形状转换。
模型对象 → 契约 Schema 的组装函数在 converters.py（避免 schemas 循环导入）。
"""

from datetime import datetime, timezone
from typing import Dict

from opentask.models.issue.enums import IssueStatus

# ============================================================================
# 状态映射默认表（S4 固定默认；S5 配置化）
# ============================================================================

ISSUE_STATUS_TO_GENERIC: Dict[str, str] = {
    IssueStatus.OPEN.value: "todo",
    IssueStatus.IN_PROGRESS.value: "in_progress",
    IssueStatus.FEEDBACK.value: "in_review",
    IssueStatus.RESOLVED.value: "done",
    IssueStatus.CLOSED.value: "done",
    IssueStatus.REJECTED.value: "cancelled",
}

GENERIC_STATUS_TO_ISSUE: Dict[str, str] = {
    "todo": IssueStatus.OPEN.value,
    "in_progress": IssueStatus.IN_PROGRESS.value,
    "in_review": IssueStatus.FEEDBACK.value,
    "done": IssueStatus.RESOLVED.value,
    "cancelled": IssueStatus.REJECTED.value,
}

GENERIC_STATUSES = frozenset(GENERIC_STATUS_TO_ISSUE)

# 契约层没有 type/priority 概念，落库时的默认值（S5 随映射表一并配置化）
DEFAULT_ISSUE_TYPE = "feature"

# 前端 issue 详情页路由（frontend/src/router/routes/index.ts: issue_detail）
ISSUE_DETAIL_PATH = "/issue/detail"


def issue_status_to_generic(status: str) -> str:
    """IssueStatus → 通用状态（全函数：6 种 IssueStatus 均有映射）"""
    try:
        return ISSUE_STATUS_TO_GENERIC[IssueStatus(status).value]
    except (KeyError, ValueError) as e:
        raise ValueError(f"未知 IssueStatus: {status!r}") from e


def generic_status_to_issue(status: str) -> str:
    """通用状态 → IssueStatus（规范逆映射；未知值抛 ValueError → 422）"""
    try:
        return GENERIC_STATUS_TO_ISSUE[status]
    except KeyError as e:
        raise ValueError(
            f"未知通用状态: {status!r}，可选值: {sorted(GENERIC_STATUSES)}"
        ) from e


def normalize_label(label: str) -> str:
    """标签规范化：去首尾空白；空串/超长直接拒绝（Tag.name 为 String(100)）"""
    normalized = label.strip() if isinstance(label, str) else ""
    if not normalized:
        raise ValueError("标签不能为空")
    if len(normalized) > 100:
        raise ValueError(f"标签过长（最大 100 字符）: {normalized[:20]}...")
    return normalized


def normalize_updated_since(value: datetime) -> datetime:
    """updated_since 游标归一化：tz-aware → naive UTC（DB 侧为 naive UTC 时间戳）"""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def build_issue_url(issue_id: str) -> str:
    """契约 url 字段：OpenTask 前端详情页相对链接（Orca 侧拼接 base URL）"""
    return f"{ISSUE_DETAIL_PATH}?id={issue_id}"
