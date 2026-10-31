"""Issue 模型 → 契约通用任务模型的组装

与 mapping.py 分离：mapping 只含词表与纯标量函数（schemas 依赖它做校验），
本模块组装 Pydantic 响应对象（依赖 schemas），避免循环导入。
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional

from opentask.models.issue.model import Issue
from opentask.models.tag.model import Tag

from .mapping import build_issue_url, issue_status_to_generic
from .schemas import ContractTask


def issue_to_contract_task(
    issue: Issue,
    *,
    tag_names_by_id: Optional[Mapping[int, str]] = None,
    usernames_by_id: Optional[Mapping[str, str]] = None,
) -> ContractTask:
    """Issue 模型 → 契约通用任务模型

    tag_names_by_id / usernames_by_id 由调用方批量预取（避免 ORM 关系懒加载）。
    """
    tag_names_by_id = tag_names_by_id or {}
    usernames_by_id = usernames_by_id or {}

    labels = sorted(
        tag_names_by_id[it.tag_id] for it in issue.tags if it.tag_id in tag_names_by_id
    )

    metadata: Dict[str, Any] = {
        "issue_code": issue.issue_code,
        "type": issue.type,
        "priority": issue.priority,
    }
    if issue.reporter_id:
        metadata["reporter_id"] = issue.reporter_id
    username = usernames_by_id.get(issue.assignee_id) if issue.assignee_id else None
    if username is not None:
        # D12：assignee 为字符串 user ID，展示名放 metadata.username
        metadata["username"] = username

    return ContractTask(
        id=issue.id,
        title=issue.title,
        description=issue.description,
        status=issue_status_to_generic(issue.status),
        assignee=issue.assignee_id,
        url=build_issue_url(issue.id),
        labels=labels,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        metadata=metadata,
    )


def issues_to_contract_tasks(
    issues: Iterable[Issue],
    *,
    tags: Iterable[Tag],
    usernames_by_id: Optional[Mapping[str, str]] = None,
) -> List[ContractTask]:
    """批量转换（列表场景）：一次预取 tags / 用户名映射，避免 N+1"""
    tag_names_by_id = {t.id: t.name for t in tags}
    return [
        issue_to_contract_task(
            issue, tag_names_by_id=tag_names_by_id, usernames_by_id=usernames_by_id or {}
        )
        for issue in issues
    ]
