"""任务源契约 API 路由（OpenTask 对接 Orca，模拟 Jira 模式）

epic ADR 落地：
- D6  按 Orca 通用任务契约暴露 REST
- D7  与现有 issue API（/api/issues）并列，不改造既有接口
- D8  DELETE 软删除（复用 is_deleted）
- D10 updated_since 时间游标（排他语义，见 service.list_issues_for_contract）
- D12 路由 /tasks 直接挂根；assignee 为字符串 user ID + metadata.username；
      labels 双向映射现有 tags 关联表

读写均经 IssueService/Issue model（权限校验路径与 UI 侧一致）。
鉴权复用现有 authenticate 依赖骨架（access_token 接入属 S5）。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.models.issue.schema import IssueCreate, IssueUpdate
from opentask.repositories.base import get_session

from .converters import issue_to_contract_task
from .mapping import (
    GENERIC_STATUSES,
    DEFAULT_ISSUE_TYPE,
    generic_status_to_issue,
)
from .schemas import ContractTask, ContractTaskListResponse, TaskCreate, TaskUpdate
from .service import (
    ContractIssueService,
    get_tag_ids_by_names,
    get_usernames_by_ids,
    sync_issue_labels,
)

logger = logging.getLogger(__name__)

# 路由直接挂根（D12）：与 UI 侧 /api/tasks（opentask/api/task/routes.py）互不冲突
router = APIRouter(prefix="/tasks", tags=["任务源契约 (Task Source Contract)"])

# 通用状态词表的查询参数校验（FastAPI 自动 422）
_GENERIC_STATUS_PATTERN = f"^({'|'.join(sorted(GENERIC_STATUSES))})$"


async def get_contract_service(
    db: AsyncSession = Depends(get_session),
) -> ContractIssueService:
    """获取契约层 Issue 服务依赖（复用 issue service，仅方言覆盖）"""
    return ContractIssueService(db)


async def _load_contract_task(
    service: ContractIssueService, task_id: str
) -> ContractTask:
    """按 ID 加载并转换为契约形状（含批量预取 tags / 用户名）"""
    issue = await service.get_issue(task_id)
    if issue is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # service.get_issue 在同一会话内二次查询时，身份映射中的旧对象不会重新装载
    # tags 集合（无 populate_existing）；变更后立即回读的场景必须显式刷新，
    # 否则 PATCH labels 后的响应会拿到旧集合
    await service.db.refresh(issue, attribute_names=["tags"])

    tag_ids = [it.tag_id for it in issue.tags]
    tag_names: dict[int, str] = {}
    if tag_ids:
        result = await service.db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        tag_names = {t.id: t.name for t in result.scalars().all()}

    usernames = await get_usernames_by_ids(
        service.db, [issue.assignee_id] if issue.assignee_id else []
    )

    return issue_to_contract_task(
        issue, tag_names_by_id=tag_names, usernames_by_id=usernames
    )


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None, pattern=_GENERIC_STATUS_PATTERN,
                                  description="通用状态过滤"),
    assignee: Optional[str] = Query(None, description="负责人 user ID 过滤"),
    updated_since: Optional[datetime] = Query(
        None, description="增量游标：仅返回 updated_at 严格大于该时刻的任务（排他）"
    ),
    limit: int = Query(50, ge=1, le=200, description="分页大小"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    service: ContractIssueService = Depends(get_contract_service),
):
    """列出任务（过滤 + 分页 + updated_since 增量游标）"""
    issue_status = generic_status_to_issue(status) if status else None
    issues, total = await service.list_issues_for_contract(
        status=issue_status,
        assignee_id=assignee,
        updated_since=updated_since,
        limit=limit,
        offset=offset,
    )

    # 批量预取标签名与用户名，避免 N+1
    tag_ids = {it.tag_id for issue in issues for it in issue.tags}
    tag_rows: list[Tag] = []
    if tag_ids:
        result = await service.db.execute(
            select(Tag).where(Tag.id.in_(list(tag_ids)))
        )
        tag_rows = list(result.scalars().all())
    assignee_ids = {i.assignee_id for i in issues if i.assignee_id}
    usernames = await get_usernames_by_ids(service.db, list(assignee_ids))

    items = [
        issue_to_contract_task(
            issue,
            tag_names_by_id={t.id: t.name for t in tag_rows},
            usernames_by_id=usernames,
        )
        for issue in issues
    ]
    return ContractTaskListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", status_code=201)
async def create_task(
    data: TaskCreate,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate),
) -> Response:
    """创建任务（title/description/assignee/status/labels 完整落库，经 issue service）"""
    issue_create = IssueCreate(
        title=data.title,
        description=data.description,
        type=DEFAULT_ISSUE_TYPE,  # type: ignore[arg-type]
        status=generic_status_to_issue(data.status or "todo"),  # type: ignore[arg-type]
        assignee_id=data.assignee,
    )
    issue = await service.create_issue(
        issue_create, str(current_user.id), dept_id=None
    )

    if data.labels:
        await sync_issue_labels(service, issue.id, data.labels, str(current_user.id))

    task = await _load_contract_task(service, issue.id)
    return JSONResponse(status_code=201, content=task.model_dump(mode="json"))


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    service: ContractIssueService = Depends(get_contract_service),
):
    """获取单个任务（软删除的不可见）"""
    return await _load_contract_task(service, task_id)


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate),
):
    """更新任务（状态变更经 issue service 写入既有 timeline）"""
    existing = await service.get_issue(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 仅透传客户端实际提供的字段（PATCH 语义）
    provided = data.model_fields_set

    issue_fields: dict = {}
    if "title" in provided:
        issue_fields["title"] = data.title
    if "description" in provided:
        issue_fields["description"] = data.description
    if "status" in provided and data.status is not None:
        issue_fields["status"] = generic_status_to_issue(data.status)
    if "assignee" in provided:
        issue_fields["assignee_id"] = data.assignee

    if issue_fields:
        update = IssueUpdate(**issue_fields)  # type: ignore[arg-type]
        await service.update_issue(task_id, update, str(current_user.id))

    if "labels" in provided and data.labels is not None:
        await sync_issue_labels(
            service, task_id, data.labels, str(current_user.id)
        )

    return await _load_contract_task(service, task_id)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate),
) -> Response:
    """删除任务（软删除，复用 is_deleted，不物理删数据）"""
    success = await service.delete_issue(task_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return Response(status_code=204)
