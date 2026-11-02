"""OAuth2 只读数据面（``/oauth2/api/*``）

口径（裁决 F）：**薄封装既有 service 层**，不改通用端点、不改 ``/tasks`` 契约层。

- 每个端点先校验 scope（``read:tasks`` / ``read:projects`` / ``read:requirements``
  / ``profile``），不足 → 403 ``insufficient_scope``；
- 数据获取一律走既有 service 层（``ContractIssueService`` / ``ProjectService`` /
  ``RequirementService``），**不复制业务逻辑、不新增查询口径**；
- 数据范围（RBAC 可见部门集）沿用既有 service 的入参约定，与通用端点一致。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from opentask.models.issue.model import Issue
from opentask.models.user.model import UserModel
from opentask.services.project_service import ProjectService
from opentask.services.user_center.rbac_service import RbacService

from .dependencies import get_oauth_session, require_oauth_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth2/api", tags=["OAuth2 API"])

# 任务列表分页上限。窗口换算用 page_size=limit（不再把 page_size 加成
# limit+remainder——那会让非对齐 offset 从错误的全局位置起取）。
TASK_PAGE_MAX = 50


@router.get("/me", summary="当前代表用户")
async def read_me(
    payload_and_user: tuple[dict, UserModel] = Depends(require_oauth_scope("profile")),
):
    """返回代表用户的基础信息"""
    _, user = payload_and_user
    return {
        "sub": str(user.id),
        "username": user.username,
        "name": user.name,
        "email": user.username,
        "role": user.role,
    }


@router.get("/tasks", summary="任务列表（只读，按成员可见集收窄）")
async def read_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤（OpenTask 原生任务状态词表）"),
    limit: int = Query(50, ge=1, le=TASK_PAGE_MAX, description="分页大小"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    payload_and_user: tuple[dict, UserModel] = Depends(
        require_oauth_scope("read:tasks")
    ),
    session: AsyncSession = Depends(get_oauth_session),
):
    """列出代表用户可见的任务

    取数口径 = **通用 issue API**（``IssueService.get_issues`` + 部门可见集），
    与 ``GET /api/issues`` 同源同口径：按该成员的 ``visible_dept_ids`` 收窄
    （外加「或本人创建」），**不是**契约层 ``/tasks`` 的取数——后者不带部门
    可见性过滤，若直接复用会把整个工作区的任务集暴露给只读 scope。

    响应形状仍沿用契约层 ``ContractTaskListResponse``（items/total/limit/offset），
    便于消费者复用解析；契约层的 service 与路由一概未改（不污染 Orca 对接面）。
    """
    from opentask.api.tasks.converters import issue_to_contract_task
    from opentask.api.tasks.service import get_usernames_by_ids
    from opentask.models.issue.enums import IssueStatus
    from opentask.models.issue.schema import IssueQueryParams
    from opentask.services.issue_service import IssueService
    from opentask.models.tag.model import Tag

    _, user = payload_and_user
    issue_status = None
    if status:
        try:
            issue_status = IssueStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_status",
                    "error_description": (
                        f"未知任务状态: {status}，可选值: "
                        f"{[item.value for item in IssueStatus]}"
                    ),
                },
            )

    # 通用 service 的 offset 是 (page-1)*page_size，不是「对齐到 limit 再多取」。
    # page_size=limit，取本页后切 [remainder:]；切完不足 limit 且本页已满，再取下一页拼上。
    # 最多两次查询。limit=10、offset=15 得到全局第 15–24 条，而不是第 20 条起。
    remainder = offset % limit
    page = offset // limit + 1
    visible_dept_ids = await RbacService(session).get_visible_dept_ids(user)
    first, total = await IssueService(session).get_issues(
        IssueQueryParams(
            page=page,
            page_size=limit,
            status=issue_status,
            sort_by="created_at",
            sort_order="asc",
        ),
        visible_dept_ids=visible_dept_ids,
        user_id=str(user.id),
    )
    window = list(first[remainder:])
    if len(window) < limit and len(first) == limit:
        second, _total = await IssueService(session).get_issues(
            IssueQueryParams(
                page=page + 1,
                page_size=limit,
                status=issue_status,
                sort_by="created_at",
                sort_order="asc",
            ),
            visible_dept_ids=visible_dept_ids,
            user_id=str(user.id),
        )
        window.extend(second[: limit - len(window)])
    issues = window

    # 通用 service 不预加载 tags 关系（契约 DTO 需要标签名）——按本页 ID 重取带
    # selectinload 的 issue，避免异步懒加载。
    if issues:
        refreshed = (
            await session.execute(
                select(Issue)
                .options(selectinload(Issue.tags))
                .where(Issue.id.in_([issue.id for issue in issues]))
            )
        ).scalars().all()
        by_id = {issue.id: issue for issue in refreshed}
        issues = [by_id[issue.id] for issue in issues if issue.id in by_id]

    # 批量预取标签名与用户名，避免 N+1（与契约层同口径）
    tag_ids = {it.tag_id for issue in issues for it in issue.tags}
    tag_names_by_id: dict = {}
    if tag_ids:
        result = await session.execute(select(Tag).where(Tag.id.in_(list(tag_ids))))
        tag_names_by_id = {tag.id: tag.name for tag in result.scalars().all()}
    assignee_ids = {i.assignee_id for i in issues if i.assignee_id}
    usernames = await get_usernames_by_ids(session, list(assignee_ids))

    items = [
        issue_to_contract_task(
            issue,
            tag_names_by_id=tag_names_by_id,
            usernames_by_id=usernames,
        )
        for issue in issues
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/projects", summary="项目列表（只读）")
async def read_projects(
    active_only: bool = Query(True, description="仅返回活跃项目"),
    payload_and_user: tuple[dict, UserModel] = Depends(
        require_oauth_scope("read:projects")
    ),
    session: AsyncSession = Depends(get_oauth_session),
):
    """列出代表用户可见的项目（RBAC 部门可见集过滤，与通用端点一致）"""
    _, user = payload_and_user
    service = ProjectService(session)
    visible_dept_ids = await RbacService(session).get_visible_dept_ids(user)
    projects = await service.list_all(active_only, visible_dept_ids=visible_dept_ids)
    return {"items": [service.to_response(project) for project in projects]}


@router.get("/requirements", summary="需求列表（只读）")
async def read_requirements(
    status: Optional[str] = Query(None, description="需求状态过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    payload_and_user: tuple[dict, UserModel] = Depends(
        require_oauth_scope("read:requirements")
    ),
    session: AsyncSession = Depends(get_oauth_session),
):
    """列出代表用户可见的需求（数据范围与通用端点一致）"""
    from opentask.api.requirement.router import get_requirement_service
    from opentask.models.requirement.model import RequirementStatus

    _, user = payload_and_user
    service = await get_requirement_service(session)
    requirement_status = None
    if status:
        try:
            requirement_status = RequirementStatus(status)
        except ValueError:
            requirement_status = None
    visible_dept_ids = await RbacService(session).get_visible_dept_ids(user)
    result = await service.get_list(
        requirement_status,
        None,
        None,
        None,
        page,
        page_size,
        visible_dept_ids=visible_dept_ids,
        user_id=str(user.id),
    )
    return result
