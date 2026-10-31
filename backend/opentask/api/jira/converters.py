"""Issue 模型 → Jira 线格式投影（探测报告 §3 的响应形状）

与 tasks/converters.py 同级并列：那边组装契约通用任务（/tasks），这边组装
Jira REST v2 形状（/rest/api/2）；状态/词表换算共用 tasks/mapping.py 内核。
"""

from typing import Any, Dict, List, Mapping, Optional

from opentask.api.tasks.mapping import (
    get_generic_statuses,
    issue_status_to_generic,
)
from opentask.models.issue.enums import IssuePriority, IssueType
from opentask.models.issue.model import Issue
from opentask.models.user.model import UserModel

from .keys import issue_code_to_key

# ============================================================================
# 通用状态 → Jira statusCategory（探测 §3：statusCategory 必须有，三键词表）
# ============================================================================

GENERIC_CATEGORY: Dict[str, str] = {
    "todo": "new",
    "in_progress": "indeterminate",
    "in_review": "indeterminate",
    "done": "done",
    "cancelled": "done",
}
# 词表外（contract.status_mapping 自定义）通用状态的兜底类目
DEFAULT_CATEGORY = "indeterminate"

CATEGORY_NAME: Dict[str, str] = {
    "new": "To Do",
    "indeterminate": "In Progress",
    "done": "Done",
}

CATEGORY_COLOR: Dict[str, str] = {
    "new": "blue-gray",
    "indeterminate": "yellow",
    "done": "green",
}


def generic_to_category(generic: str) -> str:
    return GENERIC_CATEGORY.get(generic, DEFAULT_CATEGORY)


def display_name(token: str) -> str:
    """词表 token → 展示名（todo → Todo，in_progress → In Progress）"""
    return token.replace("_", " ").title()


def generic_status_object(generic: str) -> Dict[str, Any]:
    """通用状态 → Jira status 对象（fields.status / transition.to 形状）"""
    category = generic_to_category(generic)
    return {
        "id": generic,
        "name": display_name(generic),
        "description": "",
        "iconUrl": "",
        "statusCategory": {
            "key": category,
            "name": CATEGORY_NAME.get(category, category),
            "colorName": CATEGORY_COLOR.get(category, "medium-gray"),
        },
    }


def priority_object(priority: Optional[str]) -> Optional[Dict[str, Any]]:
    """IssuePriority → Jira priority 对象（hBt 读 id/name/iconUrl）"""
    if not priority:
        return None
    return {
        "id": priority,
        "name": display_name(priority),
        "iconUrl": f"/rest/api/2/images/priorities/{priority}.svg",
    }


def issue_type_object(issue_type: str) -> Dict[str, Any]:
    """IssueType → Jira issuetype 对象（dBt 读 id/name/subtask/iconUrl）"""
    return {
        "id": issue_type,
        "name": display_name(issue_type),
        "description": "",
        "subtask": False,
        "iconUrl": f"/rest/api/2/images/issuetypes/{issue_type}.svg",
    }


def user_object(user: Optional[UserModel]) -> Optional[Dict[str, Any]]:
    """UserModel → Jira server 用户对象（VB 读 accountId ?? name ?? key）

    accountId 给 user.id（Orca ``assignee set --to-id`` 回传它），
    name/key 给 username（server 惯例）。
    """
    if user is None:
        return None
    email = getattr(user, "email", None)
    return {
        "accountId": str(user.id),
        "name": user.username or str(user.id),
        "key": user.username or str(user.id),
        "displayName": user.name or user.username or str(user.id),
        "emailAddress": email,
        "active": getattr(user, "status", 1) == 1,
        "avatarUrls": {},
    }


# ============================================================================
# 时间戳（DB naive UTC → Jira 形状 "2026-10-31T12:34:56.000+0000"）
# ============================================================================


def jira_timestamp(value) -> Optional[str]:
    if value is None:
        return None
    # DB 侧为 naive UTC；万一拿到 aware 时间统一转 UTC
    if value.tzinfo is not None:
        from datetime import timezone

        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


# ============================================================================
# Issue → Jira issue JSON（GET /issue/{key} 与 POST /search 的元素形状，UB 读法）
# ============================================================================


def issue_to_jira(
    issue: Issue,
    *,
    tag_names_by_id: Optional[Mapping[int, str]] = None,
    assignee: Optional[UserModel] = None,
    reporter: Optional[UserModel] = None,
) -> Dict[str, Any]:
    """Issue 模型 → Jira issue 对象（fields 子集按 Orca 实际读取面投影）"""
    tag_names_by_id = tag_names_by_id or {}
    labels = sorted(
        tag_names_by_id[it.tag_id] for it in issue.tags if it.tag_id in tag_names_by_id
    )
    description = issue.description or ""
    return {
        "id": issue.id,
        "key": issue_code_to_key(issue.issue_code),
        "fields": {
            "summary": issue.title,
            # server 模式描述为纯文本字符串（探测 §3，HB：server 透传原文）
            "description": description,
            "project": PROJECT_OBJECT,
            "issuetype": issue_type_object(issue.type),
            "status": generic_status_object(issue_status_to_generic(issue.status)),
            "labels": labels,
            "assignee": user_object(assignee),
            "reporter": user_object(reporter),
            "priority": priority_object(issue.priority),
            "parent": None,
            "created": jira_timestamp(issue.created_at),
            "updated": jira_timestamp(issue.updated_at),
            "timeoriginalestimate": None,
            "timeestimate": None,
            "attachment": [],
        },
        # expand=renderedFields 的读取面只有 description（iVt/QBt）
        "renderedFields": {"description": description},
    }


# 虚拟单项目：OpenTask 无 Jira 项目概念，投影为常量（探测 §5）
PROJECT_OBJECT: Dict[str, Any] = {
    "id": "OPENTASK",
    "key": "OPENTASK",
    "name": "OpenTask",
}


def available_transitions(current_generic: str) -> List[Dict[str, Any]]:
    """当前通用状态 → 可流转列表（目标为词表内其余全部状态）

    transition.id = 目标通用状态 token（唯一、可直接回传）；
    name = token（CLI ``--to in_progress`` 精确命中）、
    to.name = 展示名（``--to "In Progress"`` 命中）——两侧都可达。
    """
    return [
        {"id": token, "name": token, "to": generic_status_object(token)}
        for token in sorted(get_generic_statuses())
        if token != current_generic
    ]


def priority_catalog() -> List[Dict[str, Any]]:
    """GET /priority 响应体（IssuePriority 全词表）"""
    return [priority_object(p.value) for p in IssuePriority]  # type: ignore[misc]


def issue_type_catalog() -> List[Dict[str, Any]]:
    """GET /issue/createmeta/{project}/issuetypes 的 values 元素形状"""
    return [issue_type_object(t.value) for t in IssueType]  # type: ignore[misc]
