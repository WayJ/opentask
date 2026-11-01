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

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.services.project_service import ProjectService
from opentask.services.user_center.rbac_service import RbacService

from .dependencies import get_oauth_session, require_oauth_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth2/api", tags=["OAuth2 API"])


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


@router.get("/tasks", summary="任务列表（只读）")
async def read_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="分页大小"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    payload_and_user: tuple[dict, UserModel] = Depends(
        require_oauth_scope("read:tasks")
    ),
    session: AsyncSession = Depends(get_oauth_session),
):
    """列出代表用户可见的任务

    数据来源与口径与契约层 ``GET /tasks`` 一致（同一 service 方法），
    但走 OAuth2 只读面——带 ``aud`` 的 OAuth token 进不了 ``/tasks``。
    """
    from opentask.api.tasks.converters import issue_to_contract_task
    from opentask.api.tasks.service import ContractIssueService, get_usernames_by_ids
    from opentask.api.tasks.mapping import generic_status_to_issue_set
    from opentask.models.tag.model import Tag

    _, user = payload_and_user
    issue_statuses = generic_status_to_issue_set(status) if status else None
    service = ContractIssueService(session)
    issues, total = await service.list_issues_for_contract(
        status=issue_statuses,
        assignee_id=None,
        limit=limit,
        offset=offset,
    )

    # 批量预取标签名与用户名，避免 N+1（与契约层同口径）
    from sqlalchemy import select

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
