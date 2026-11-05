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
- S6  错误语义定稿（errors.py）：401 CONTRACT_AUTH_* / 403
      CONTRACT_FORBIDDEN（contract.forbidden_operations 禁操作）/
      404 CONTRACT_TASK_NOT_FOUND / 422 CONTRACT_STATUS_UNKNOWN /
      503 CONTRACT_UNAVAILABLE（get_contract_session 依赖探测）；
      全部契约端点经 responses= 声明错误响应模型
      （spec 导出见 openapi_export.py → backend/openapi_contract.json）。

读写均经 IssueService/Issue model（权限校验路径与 UI 侧一致）。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.models.issue.schema import IssueCreate, IssueUpdate

from .auth import authenticate_contract, exchange_client_credentials
from .converters import issue_to_contract_task
from .errors import (
    CODE_FORBIDDEN,
    CODE_STATUS_UNKNOWN,
    CODE_TASK_NOT_FOUND,
    ERR_400_GRANT,
    ERR_401,
    ERR_403,
    ERR_404,
    ERR_422,
    ERR_503,
    contract_error,
    get_contract_session,
)
from .mapping import (
    generic_status_to_issue,
    generic_status_to_issue_set,
    get_contract_mapping,
    get_default_generic_status,
    get_default_issue_type,
    get_forbidden_operations,
    get_generic_statuses,
)
from opentask.services.workspace.issue_create_ws import (
    WorkspaceRequiredError,
    resolve_workspace_for_issue_create,
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
    db: AsyncSession = Depends(get_contract_session),
) -> ContractIssueService:
    """获取契约层 Issue 服务依赖（复用 issue service，仅方言覆盖；会话先经可用性探测）"""
    return ContractIssueService(db)


def _validate_generic_status(status: str) -> str:
    """通用状态值运行时校验：词表随配置可变（违例 422 CONTRACT_STATUS_UNKNOWN）

    词表依赖生效配置、无法静态穷举，故不经 pydantic 静态校验
    （schemas.TaskCreate/TaskUpdate 的 status 字段无静态词表约束）。
    """
    try:
        generic_status_to_issue(status)
    except ValueError as e:
        raise contract_error(422, CODE_STATUS_UNKNOWN, str(e)) from e
    return status


def _ensure_operation_allowed(operation: str) -> None:
    """禁操作校验（403 CONTRACT_FORBIDDEN）：被 contract.forbidden_operations 命中即拒

    在鉴权依赖之后、业务逻辑之前调用，保证 401 优先于 403
    （未认证请求无从谈禁不禁）。
    """
    if operation in get_forbidden_operations():
        raise contract_error(
            403,
            CODE_FORBIDDEN,
            f"操作 {operation} 已被禁用（contract.forbidden_operations），"
            "请联系 OpenTask 管理员调整配置",
        )


async def _load_contract_task(
    service: ContractIssueService, task_id: str
) -> ContractTask:
    """按 ID 加载并转换为契约形状（含批量预取 tags / 用户名）"""
    issue = await service.get_issue(task_id)
    if issue is None:
        raise contract_error(404, CODE_TASK_NOT_FOUND, f"任务不存在: {task_id}")

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


@router.get(
    "/tasks",
    response_model=ContractTaskListResponse,
    responses={**ERR_401, **ERR_403, **ERR_422, **ERR_503},
)
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
    _ensure_operation_allowed("list_tasks")
    if status is not None:
        _validate_generic_status(status)
        # 过滤按正映射集合匹配（done → {resolved, closed}），
        # 与列表正向展示口径一致；单值逆映射会漏数据
        issue_statuses = generic_status_to_issue_set(status)
    else:
        issue_statuses = None
    issues, total = await service.list_issues_for_contract(
        status=issue_statuses,
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


@router.post(
    "/tasks",
    status_code=201,
    response_model=ContractTask,
    responses={**ERR_401, **ERR_403, **ERR_422, **ERR_503},
)
async def create_task(
    data: TaskCreate,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
) -> ContractTask:
    """创建任务（title/description/assignee/status/labels 完整落库，经 issue service）"""
    _ensure_operation_allowed("create_task")
    # 默认状态自生效配置推导（词表可合法省略 todo，硬编码会 500）
    status = data.status or get_default_generic_status()
    _validate_generic_status(status)
    issue_create = IssueCreate(
        title=data.title,
        description=data.description,
        type=get_default_issue_type(),  # type: ignore[arg-type]
        status=generic_status_to_issue(status),  # type: ignore[arg-type]
        assignee_id=data.assignee,
    )
    try:
        workspace_id = await resolve_workspace_for_issue_create(
            service.db, str(current_user.id)
        )
    except WorkspaceRequiredError as e:
        raise HTTPException(status_code=400, detail=e.detail) from e
    issue = await service.create_issue(
        issue_create, str(current_user.id), dept_id=None, workspace_id=workspace_id
    )

    if data.labels:
        await sync_issue_labels(service, issue.id, data.labels, str(current_user.id))

    return await _load_contract_task(service, issue.id)


@router.get(
    "/tasks/{task_id}",
    response_model=ContractTask,
    responses={**ERR_401, **ERR_403, **ERR_404, **ERR_503},
)
async def get_task(
    task_id: str,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
):
    """获取单个任务（软删除的不可见）"""
    _ensure_operation_allowed("get_task")
    return await _load_contract_task(service, task_id)


@router.patch(
    "/tasks/{task_id}",
    response_model=ContractTask,
    responses={**ERR_401, **ERR_403, **ERR_404, **ERR_422, **ERR_503},
)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
):
    """更新任务（状态变更经 issue service 写入既有 timeline）"""
    _ensure_operation_allowed("update_task")
    existing = await service.get_issue(task_id)
    if existing is None:
        raise contract_error(404, CODE_TASK_NOT_FOUND, f"任务不存在: {task_id}")

    # 仅透传客户端实际提供的字段（PATCH 语义）
    provided = data.model_fields_set

    issue_fields: dict = {}
    if "title" in provided:
        issue_fields["title"] = data.title
    if "description" in provided:
        issue_fields["description"] = data.description
    if "status" in provided and data.status is not None:
        _validate_generic_status(data.status)
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


@router.delete(
    "/tasks/{task_id}",
    status_code=204,
    responses={**ERR_401, **ERR_403, **ERR_404, **ERR_503},
)
async def delete_task(
    task_id: str,
    service: ContractIssueService = Depends(get_contract_service),
    current_user: UserModel = Depends(authenticate_contract),
) -> Response:
    """删除任务（软删除，复用 is_deleted，不物理删数据）"""
    _ensure_operation_allowed("delete_task")
    success = await service.delete_issue(task_id, str(current_user.id))
    if not success:
        raise contract_error(404, CODE_TASK_NOT_FOUND, f"任务不存在: {task_id}")
    return Response(status_code=204)


# ============================================================================
# 鉴权（OAuth2 client credentials：API Key → 短时效 JWT）
# ============================================================================


@router.post(
    "/tasks/token",
    responses={**ERR_400_GRANT, **ERR_401, **ERR_503},
)
async def issue_contract_token(
    grant_type: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_contract_session),
):
    """OAuth2 client credentials 换 token（公开端点，凭证即 API Key）

    - grant_type=client_credentials（固定值）
    - client_secret：``vk_`` API Key（必填）
    - client_id：可选，提供时须为该 Key 归属用户 ID
    返回 ``{access_token, token_type: "Bearer", expires_in}``（不下发 refresh）。
    """
    return await exchange_client_credentials(
        session,
        grant_type=grant_type,
        client_id=client_id,
        client_secret=client_secret,
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
            # 禁操作表实时下发（消费方可据此隐藏入口/提前拦截；
            # "none" = 全放行）
            "forbidden_operations": ",".join(sorted(mapping.forbidden_operations))
            or "none",
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
