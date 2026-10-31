"""任务源契约 API 路由（OpenTask 对接 Orca，模拟 Jira 模式）

epic ADR 落地：
- D6  按 Orca 通用任务契约暴露 REST
- D7  与现有 issue API（/api/issues）并列，不改造既有接口
- D8  DELETE 软删除（复用 is_deleted）
- D10 updated_since 时间游标（排他语义，见 service.list_issues_for_contract）
- D12 路由挂根；assignee 为字符串 user ID + metadata.username；
      labels 双向映射现有 tags 关联表
- S5  鉴权走契约层 authenticate_contract（API Key + client credentials，
      401 独立语义带错误码字段）；/tasks/token 与 /capabilities 公开；
      路由本身无前缀（/tasks/* 与 /capabilities 均为完整路径），
      挂载处（app.py）不再叠加全局 authenticate 依赖。

读写均经 IssueService/Issue model（权限校验路径与 UI 侧一致）。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.models.issue.schema import IssueCreate, IssueUpdate
from opentask.repositories.base import get_session

from .auth import authenticate_contract, exchange_client_credentials
from .converters import issue_to_contract_task
from .mapping import (
    generic_status_to_issue,
    get_contract_mapping,
    get_default_issue_type,
    get_generic_statuses,
)
from .schemas import (
    CONTRACT_VERSION,
    ContractCapabilities,
    ContractTask,
    ContractTaskListResponse,
    TaskCreate,
    TaskUpdate,
)
from .service import (
    ContractIssueService,
    get_tag_ids_by_names,
    get_usernames_by_ids,
    sync_issue_labels,
)

logger = logging.getLogger(__name__)

# 无前缀：/tasks/* 与 /capabilities 都是完整路径（见模块 docstring，D12+S5）
router = APIRouter(tags=["任务源契约 (Task Source Contract)"])


async def get_contract_service(
    db: AsyncSession = Depends(get_session),
) -> ContractIssueService:
    """获取契约层 Issue 服务依赖（复用 issue service，仅方言覆盖）"""
    return ContractIssueService(db)


def _validate_generic_status(status: str) -> str:
    """通用状态查询参数校验：词表随配置可变，须运行时校验（违例 422）"""
    try:
        generic_status_to_issue(status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return status


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


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(
        None, description="通用状态过滤（词表见 GET /capabilities.status_vocabulary）"
    ),
    assignee: Optional[str] = Query(None, description="负责人 user ID 过滤"),
    updated_since: Optional[datetime] = Query(
        None, description="增量游标：仅返回 updated_at 严格大于该时刻的任务（排他）"
    ),
    limit: int = Query(50, ge=1, le=200, description="分页大小"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
):
    """列出任务（过滤 + 分页 + updated_since 增量游标）"""
    if status is not None:
        _validate_generic_status(status)
        issue_status = generic_status_to_issue(status)
    else:
        issue_status = None
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


@router.post("/tasks", status_code=201)
async def create_task(
    data: TaskCreate,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
) -> Response:
    """创建任务（title/description/assignee/status/labels 完整落库，经 issue service）"""
    issue_create = IssueCreate(
        title=data.title,
        description=data.description,
        type=get_default_issue_type(),  # type: ignore[arg-type]
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


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
):
    """获取单个任务（软删除的不可见）"""
    return await _load_contract_task(service, task_id)


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
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


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
) -> Response:
    """删除任务（软删除，复用 is_deleted，不物理删数据）"""
    success = await service.delete_issue(task_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return Response(status_code=204)


# ============================================================================
# 鉴权（OAuth2 client credentials：API Key → 短时效 JWT）
# ============================================================================


@router.post("/tasks/token")
async def issue_contract_token(
    request: Request,
    grant_type: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
):
    """OAuth2 client credentials 换 token（公开端点，凭证即 API Key）

    - grant_type=client_credentials（固定值）
    - client_secret：``vk_`` API Key（必填）
    - client_id：可选，提供时须为该 Key 归属用户 ID
    返回 ``{access_token, token_type: "Bearer", expires_in}``（不下发 refresh）。
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    return await exchange_client_credentials(
        session,
        grant_type=grant_type,
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        ip=client_ip,
    )


# ============================================================================
# 能力声明（公开端点）
# ============================================================================


@router.get("/capabilities", response_model=ContractCapabilities)
async def capabilities() -> ContractCapabilities:
    """契约能力声明：端点支持情况 + 契约版本 + 鉴权模式 + 生效状态词表

    无需凭证（对接前探测用）；不含敏感信息，仅描述契约形状。
    """
    mapping = get_contract_mapping()
    return ContractCapabilities(
        contract_version=CONTRACT_VERSION,
        endpoints={
            "list_tasks": "GET /tasks",
            "create_task": "POST /tasks",
            "get_task": "GET /tasks/{task_id}",
            "update_task": "PATCH /tasks/{task_id}",
            "delete_task": "DELETE /tasks/{task_id}",
            "issue_token": "POST /tasks/token",
            "capabilities": "GET /capabilities",
        },
        features={
            "pagination": "limit_offset",
            "incremental_cursor": "updated_since",
            "cursor_semantics": "exclusive",
            "delete_semantics": "soft",
            "status_mapping_source": mapping.source,
        },
        auth={
            "modes": ["bearer_api_key", "oauth2_client_credentials"],
            "scheme": "Bearer",
            "token_endpoint": "/tasks/token",
            "grant_type": "client_credentials",
            "api_key_prefix": "vk_",
        },
        status_vocabulary=sorted(get_generic_statuses()),
    )
