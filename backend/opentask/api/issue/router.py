"""Issue API 路由"""
import logging
from typing import List, Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.models.requirement.model import Project
from opentask.models.user.model import UserModel
from opentask.auth import authenticate
from opentask.models.issue.schema import (
    IssueCreate,
    IssueUpdate,
    IssueResponse,
    IssueChildSummary,
    IssueListResponse,
    IssueCommentBase,
    IssueCommentRequest,
    IssueCommentCreate,
    IssueCommentUpdate,
    IssueCommentResponse,
    IssueRelationCreate,
    IssueRelationResponse,
    IssueTimelineResponse,
    IssueQueryParams,
    IssueBulkUpdate,
    IssueBulkDelete,
    IssueBoardMove,
    IssueStatistics,
    IssueReactionCreate,
    IssueReactionResponse,
    IssueReactionStats,
    UserInfo,
)
from opentask.models.issue_collection.schema import (
    IssueCollectionCreate,
    IssueCollectionUpdate,
    IssueCollectionResponse,
    IssueCollectionListResponse,
    CollectionStatistics,
    IssueParseRequest,
    IssueParseResponse,
)
from opentask.models.issue.enums import RelationType
from opentask.services.issue_service import IssueService
from opentask.services.issue_template.service import IssueTemplateService
from opentask.services.tag.service import (
    TagService,
    load_tags_for_issues,
    require_writer as require_tag_writer,
    serialize_tag_brief,
)
from opentask.services.custom_field.service import CustomFieldService, parse_cf_query_items, require_writer as require_cf_writer
from opentask.services.issue_csv import IssueCsvService, require_writer as require_csv_writer, EXPORT_MAX_ROWS
from opentask.api.workspace.deps import get_optional_workspace_context, require_workspace_context, ensure_entity_workspace_access
from opentask.models.workspace.model import Workspace, WorkspaceMember
from pydantic import BaseModel, Field
from opentask.services.user_center.rbac_service import RbacService
from opentask.services.workspace.service import WorkspaceService
from opentask.services.storage.service import get_storage_service
from opentask.services.issue_collection_service import IssueCollectionService
from opentask.auth import authenticate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/issues", tags=["Issue 管理"])


async def get_issue_service(
    db: AsyncSession = Depends(get_session)
) -> IssueService:
    """获取 Issue 服务依赖"""
    return IssueService(db)


async def _require_issue_access(
    issue_id: str,
    *,
    service: IssueService,
    user: UserModel,
    by_code: bool = False,
    workspace_id: str | None = None,
):
    """E15：加载 Issue 并校验调用者对其 workspace_id 的成员资格。"""
    issue = await service.get_issue(issue_id, by_code=by_code, workspace_id=workspace_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue 不存在")
    await ensure_entity_workspace_access(service.db, str(user.id), issue.workspace_id)
    return issue


async def _require_comment_issue_access(
    comment_id: str,
    *,
    service: IssueService,
    user: UserModel,
):
    """E15：按评论所属 Issue 校验成员。"""
    from opentask.models.issue.model import IssueComment

    result = await service.db.execute(
        select(IssueComment).where(
            IssueComment.id == comment_id,
            IssueComment.is_deleted == False,
        )
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(status_code=404, detail="评论不存在")
    await _require_issue_access(comment.issue_id, service=service, user=user)
    return comment




# ========================================================================
# Issue CRUD 操作
# ========================================================================

@router.get("")
async def get_issues(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: Optional[str] = Query(None, description="类型筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选"),
    project_id: Optional[str] = Query(None, description="项目 ID"),
    assignee_id: Optional[str] = Query(None, description="负责人 ID；传 me 表示当前用户"),
    reporter_id: Optional[str] = Query(None, description="报告人 ID；传 me 表示当前用户"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    cycle_id: Optional[str] = Query(None, description="Cycle ID；__none__ 表示无 Cycle"),
    milestone_id: Optional[str] = Query(None, description="Milestone ID；__none__ 表示无里程碑"),
    watching: Optional[bool] = Query(None, description="E19：仅我关注的"),
    due_before: Optional[str] = Query(None, description="E19：due_date ≤ YYYY-MM-DD"),
    due_soon: Optional[bool] = Query(None, description="E19：3 日内到期且未关闭"),
    include: Optional[str] = Query(None, description="E25：逗号分隔附加；custom_fields"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
    ws_ctx=Depends(get_optional_workspace_context),
):
    """获取 Issue 列表（部门数据范围 + 工作区隔离）"""
    workspace, _member, user = ws_ctx
    resolved_assignee = str(user.id) if assignee_id == "me" else assignee_id
    resolved_reporter = str(user.id) if reporter_id == "me" else reporter_id
    params = IssueQueryParams(
        page=page,
        page_size=page_size,
        type=type,  # type: ignore
        status=status,  # type: ignore
        priority=priority,  # type: ignore
        project_id=project_id,
        assignee_id=resolved_assignee,
        reporter_id=resolved_reporter,
        search=search,
        cycle_id=cycle_id,
        milestone_id=milestone_id,
        watching=watching,
        due_before=due_before,
        due_soon=due_soon,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # E32：cf.<key>=value 或 cf=key=value
    cf_filters = parse_cf_query_items(list(request.query_params.multi_items()))

    ws_id = workspace.id if workspace is not None else None
    allowed = None
    if workspace is None:
        allowed = await WorkspaceService(service.db).member_workspace_ids(str(user.id))
        visible_dept_ids = await RbacService(service.db).get_visible_dept_ids(user)
    else:
        # 显式工作区：租户隔离优先，跳过部门 SELF 空集
        visible_dept_ids = None
    issues, total = await service.get_issues(
        params,
        visible_dept_ids=visible_dept_ids,
        user_id=str(user.id),
        workspace_id=ws_id,
        allowed_workspace_ids=allowed,
        custom_field_filters=cf_filters or None,
    )

    # 使用 IssueResponse 的 field_validator 自动处理用户信息转换
    tag_map = await load_tags_for_issues(service.db, issues)
    block_map = await service.relation_block_counts([i.id for i in issues])
    include_set = {p.strip() for p in (include or "").split(",") if p.strip()}
    cf_map = {}
    if "custom_fields" in include_set and ws_id is not None:
        cf_map = await CustomFieldService(service.db).values_for_issues(
            workspace_id=ws_id, issue_ids=[i.id for i in issues]
        )
    rows = []
    for issue in issues:
        payload = IssueResponse.model_validate(issue).model_dump(mode="json", exclude_none=False)
        payload["tags"] = [serialize_tag_brief(t) for t in tag_map.get(issue.id, [])]
        counts = block_map.get(issue.id, {"blocks_count": 0, "blocked_by_count": 0})
        payload["blocks_count"] = counts["blocks_count"]
        payload["blocked_by_count"] = counts["blocked_by_count"]
        if "custom_fields" in include_set:
            payload["customFields"] = cf_map.get(issue.id, [])
        rows.append(payload)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": rows,
            "total": total,
            "current": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
        },
        "timestamp": 0,
    }



# ============================================================================
# E28 · CSV Import / Export（静态路径，须在 /{issue_id} 之前）
# ============================================================================


@router.get("/export.csv")
async def export_issues_csv(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None, description="负责人；me=当前用户"),
    cycle_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    service: IssueService = Depends(get_issue_service),
    ctx: tuple = Depends(require_workspace_context),
):
    """E28：导出当前工作区 Issue 为 CSV（viewer+）。"""
    workspace, _member, user = ctx
    resolved_assignee = str(user.id) if assignee_id == "me" else assignee_id
    csv_svc = IssueCsvService(service.db)
    body, truncated = await csv_svc.build_export_csv(
        workspace_id=workspace.id,
        status=status,
        priority=priority,
        type=type,
        project_id=project_id,
        assignee_id=resolved_assignee,
        cycle_id=cycle_id,
        search=search,
        max_rows=EXPORT_MAX_ROWS,
    )
    headers = {
        "Content-Disposition": 'attachment; filename="issues-export.csv"',
    }
    if truncated:
        headers["X-Export-Truncated"] = "true"
    return StreamingResponse(
        iter([body]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/import/template.csv")
async def download_import_template(
    service: IssueService = Depends(get_issue_service),
    ctx: tuple = Depends(require_workspace_context),
):
    """E28：下载导入模板 CSV（viewer+）。"""
    _workspace, _member, _user = ctx
    body = IssueCsvService(service.db).template_csv()
    return StreamingResponse(
        iter([body]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="issues-import-template.csv"'},
    )


@router.post("/import")
async def import_issues_csv(
    file: UploadFile = File(...),
    service: IssueService = Depends(get_issue_service),
    ctx: tuple = Depends(require_workspace_context),
):
    """E28：CSV 导入（member+）；单行失败不阻断。"""
    workspace, member, user = ctx
    require_csv_writer(member)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    result = await IssueCsvService(service.db).import_csv(
        workspace_id=workspace.id,
        user_id=str(user.id),
        content=raw,
    )
    return {
        "code": 200,
        "message": "success",
        "data": result,
        "timestamp": 0,
    }


@router.post("/batch")
async def get_issues_by_ids(
    request: Request,
    service: IssueService = Depends(get_issue_service),
):
    """批量获取 Issues

    接受 JSON 格式的 ID 列表：
    {
        "ids": ["id1", "id2", "id3"]
    }

    最多支持 100 个 IDs
    """
    import json

    try:
        # 解析请求体
        body = await request.json()
        issue_ids = body.get("ids", [])

        if not issue_ids:
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "rows": [],
                    "total": 0
                },
                "timestamp": 0,
            }

        # 批量查询
        issues = await service.get_issues_by_ids(issue_ids)

        # 转换为响应格式
        rows = [IssueResponse.model_validate(issue).model_dump(mode='json', exclude_none=False) for issue in issues]

        return {
            "code": 200,
            "message": "success",
            "data": {
                "rows": rows,
                "total": len(rows)
            },
            "timestamp": 0,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"批量获取 Issues 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_issue(
    data: IssueCreate,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
    ws_ctx=Depends(get_optional_workspace_context),
):
    """创建 Issue（可选 X-Workspace-Id；可选 template_id 合并模板 payload）"""

    try:
        workspace, _member, user = ws_ctx
        # E9-S2：template_id → 合并 payload（body 非空 title 保留）
        if data.template_id:
            if workspace is None:
                raise HTTPException(status_code=400, detail="使用模板需要 X-Workspace-Id")
            tpl = await IssueTemplateService(service.db).get(
                workspace_id=workspace.id, template_id=data.template_id
            )
            merged = IssueTemplateService.apply_template_defaults(
                tpl.payload or {}, data.model_dump()
            )
            # drop template_id before Issue(**)
            merged.pop("template_id", None)
            data = IssueCreate(**merged)
        # 部门归属快照：取创建人主部门
        dept_id = await RbacService(service.db).get_primary_dept_id(user)
        issue = await service.create_issue(
            data,
            str(user.id),
            dept_id=dept_id,
            workspace_id=workspace.id if workspace else None,
        )
        return {
            "code": 200,
            "message": "Issue 创建成功",
            "data": IssueResponse.model_validate(issue),
            "timestamp": 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建 Issue 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/board/move")
async def move_issue_on_board(
    data: IssueBoardMove,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
    ws_ctx=Depends(get_optional_workspace_context),
):
    """看板拖拽落盘：原子更新 status + position（可选 ordered_ids 同列重排）。

    若带 X-Workspace-Id，则校验 Issue 属于该工作区。
    """
    workspace, _member, user = ws_ctx
    try:
        issue = await service.move_issue_on_board(
            data,
            str(user.id),
            workspace_id=workspace.id if workspace else None,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"看板移动 Issue 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "code": 200,
        "message": "Issue 看板位置已更新",
        "data": IssueResponse.model_validate(issue),
        "timestamp": 0,
    }


# ========================================================================
# Issue Collection (问题集) 管理接口
# 注意：这些路由必须在 /{issue_id} 之前定义，避免路由冲突
# ========================================================================

async def collection_to_response(collection, db: AsyncSession) -> dict:
    """将 IssueCollection 模型转换为响应字典，并加载 creator 关系"""
    # 尝试加载创建人信息
    creator_data = None
    if collection.creator_id:
        try:
            user_result = await db.execute(
                select(UserModel).where(UserModel.id == collection.creator_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                creator_data = {
                    "id": str(user.id),
                    "name": user.name,
                    "sso_name": user.sso_name,
                    "sso_account": user.sso_account
                }
        except Exception as e:
            logger.warning(f"Failed to load creator for collection {collection.id}: {e}")

    return {
        "id": collection.id,
        "title": collection.title,
        "description": collection.description,
        "status": collection.status,
        "issue_ids": collection.issue_ids or [],
        "creator_id": collection.creator_id,
        "created_at": collection.created_at,
        "updated_at": collection.updated_at,
        "creator": creator_data,
        "statistics": None
    }


async def get_collection_service(
    db: AsyncSession = Depends(get_session)
) -> IssueCollectionService:
    """获取问题集服务依赖"""
    return IssueCollectionService(db)


@router.get("/collections", tags=["问题集管理"])
async def get_collections(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    creator_id: Optional[str] = Query(None, description="创建人 ID"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    service: IssueCollectionService = Depends(get_collection_service),
    db: AsyncSession = Depends(get_session),
):
    """获取问题集列表"""
    collections, total = await service.get_collections(
        page=page,
        page_size=page_size,
        status=status,
        creator_id=creator_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # 使用辅助函数转换为响应格式
    items = [IssueCollectionResponse(**await collection_to_response(c, db)) for c in collections]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": items,
            "total": total,
            "current": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
        },
        "timestamp": 0,
    }


@router.get("/collections/{collection_id}", tags=["问题集管理"])
async def get_collection(
    collection_id: str,
    service: IssueCollectionService = Depends(get_collection_service),
    db: AsyncSession = Depends(get_session),
):
    """获取问题集详情"""
    collection = await service.get_collection_by_id(collection_id)

    if not collection:
        raise HTTPException(status_code=404, detail="问题集不存在")

    # 获取统计信息
    statistics = await service.get_collection_statistics(collection_id)

    # 使用辅助函数转换为响应格式
    response_data = await collection_to_response(collection, db)
    response_data["statistics"] = statistics
    response = IssueCollectionResponse(**response_data)

    return {
        "code": 200,
        "message": "success",
        "data": response.model_dump(mode='json', exclude_none=False),
        "timestamp": 0,
    }


@router.post("/collections", tags=["问题集管理"])
async def create_collection(
    data: IssueCollectionCreate,
    current_user: UserModel = Depends(authenticate),
    service: IssueCollectionService = Depends(get_collection_service),
    db: AsyncSession = Depends(get_session),
):
    """创建问题集"""
    user_id = str(current_user.id)

    collection = await service.create_collection(data, user_id)

    # 使用辅助函数转换为响应格式
    response_data = await collection_to_response(collection, db)
    response = IssueCollectionResponse(**response_data)

    return {
        "code": 200,
        "message": "创建成功",
        "data": response.model_dump(mode='json', exclude_none=False),
        "timestamp": 0,
    }


@router.put("/collections/{collection_id}", tags=["问题集管理"])
async def update_collection(
    collection_id: str,
    data: IssueCollectionUpdate,
    current_user: UserModel = Depends(authenticate),
    service: IssueCollectionService = Depends(get_collection_service),
    db: AsyncSession = Depends(get_session),
):
    """更新问题集"""
    collection = await service.update_collection(collection_id, data)

    if not collection:
        raise HTTPException(status_code=404, detail="问题集不存在")

    # 使用辅助函数转换为响应格式
    response_data = await collection_to_response(collection, db)
    response = IssueCollectionResponse(**response_data)

    return {
        "code": 200,
        "message": "更新成功",
        "data": response.model_dump(mode='json', exclude_none=False),
        "timestamp": 0,
    }


@router.delete("/collections/{collection_id}", tags=["问题集管理"])
async def delete_collection(
    collection_id: str,
    current_user: UserModel = Depends(authenticate),
    service: IssueCollectionService = Depends(get_collection_service),
):
    """删除问题集"""
    success = await service.delete_collection(collection_id)

    if not success:
        raise HTTPException(status_code=404, detail="问题集不存在")

    return {
        "code": 200,
        "message": "删除成功",
        "data": None,
        "timestamp": 0,
    }


@router.post("/collections/{collection_id}/parse", tags=["问题集管理"])
async def parse_collection(
    collection_id: str,
    request_data: IssueParseRequest,
    current_user: UserModel = Depends(authenticate),
    service: IssueCollectionService = Depends(get_collection_service),
):
    """拆解问题集并创建 Issue

    此 API 供外部服务调用（如 AI 解析服务），将问题集拆解为具体的 Issue。
    """
    import datetime
    print(f"[DEBUG {datetime.datetime.now()}] parse_collection called with collection_id={collection_id}")
    print(f"[DEBUG] issues count: {len(request_data.issues)}")

    user_id = str(current_user.id)
    print(f"[DEBUG] user_id: {user_id}")

    # 执行拆解和创建
    issue_ids, count = await service.parse_and_create_issues(
        collection_id=collection_id,
        issues_data=request_data.issues,
        creator_id=user_id,
    )

    print(f"[DEBUG] Created {count} issues: {issue_ids}")

    return {
        "code": 200,
        "message": f"成功创建 {count} 个 Issue",
        "data": {
            "parsed_count": count,
            "issue_ids": issue_ids,
        },
        "timestamp": 0,
    }


@router.get("/collections/{collection_id}/statistics", tags=["问题集管理"])
async def get_collection_statistics(
    collection_id: str,
    service: IssueCollectionService = Depends(get_collection_service),
):
    """获取问题集统计信息"""
    statistics = await service.get_collection_statistics(collection_id)

    if not statistics:
        raise HTTPException(status_code=404, detail="问题集不存在")

    return {
        "code": 200,
        "message": "success",
        "data": statistics.model_dump(),
        "timestamp": 0,
    }


# ========================================================================
# Issue CRUD 操作
# ========================================================================

@router.get("/statistics")
async def get_statistics(
    project_id: Optional[str] = Query(None, description="项目 ID"),
    service: IssueService = Depends(get_issue_service),
):
    """获取 Issue 统计信息"""
    stats = await service.get_statistics(project_id)

    return {
        "code": 200,
        "message": "success",
        "data": stats,
        "timestamp": 0,
    }


@router.get("/{issue_id}")
async def get_issue(
    issue_id: str,
    by_code: bool = Query(False, description="是否通过 issue_code 查询（默认通过 ID 查询）"),
    service: IssueService = Depends(get_issue_service),
    db: AsyncSession = Depends(get_session),
    ws_ctx=Depends(get_optional_workspace_context),
):
    """获取 Issue 详情

    Args:
        issue_id: Issue ID 或 Issue Code
        by_code: 设为 true 时，通过 issue_code / legacy_issue_code 查询；默认通过 ID 查询

    Examples:
        GET /api/issues/5ee3420e-2d69-4509-9ae7-524e8c40d6d1  # 通过 ID 查询
        GET /api/issues/OT-1?by_code=true                  # 通过 KEY-N 查询
        GET /api/issues/ISSUE2026-32?by_code=true          # 通过 legacy code 查询
    """
    workspace, _member, user = ws_ctx
    # by_code 仍用 header WS 精确过滤（不回退）；按 UUID 不靠 header，靠实体 membership
    workspace_id = workspace.id if (workspace is not None and by_code) else None
    issue = await _require_issue_access(
        issue_id, service=service, user=user, by_code=by_code, workspace_id=workspace_id
    )

    # 转换为字典，使用 mode='json' 确保所有字段都被序列化
    issue_dict = IssueResponse.model_validate(issue).model_dump(mode='json', exclude_none=False)
    detail_tags = await load_tags_for_issues(db, [issue])
    issue_dict["tags"] = [serialize_tag_brief(t) for t in detail_tags.get(issue.id, [])]

    # E25：详情默认带 customFields
    cf_map = await CustomFieldService(db).values_for_issues(
        workspace_id=issue.workspace_id, issue_ids=[issue.id]
    )
    issue_dict["customFields"] = cf_map.get(issue.id, [])

    # E4-S3：子 Issue 轻量摘要
    children = await service.list_child_issues(issue.id)
    issue_dict["children"] = [
        IssueChildSummary(
            id=c.id,
            issue_code=c.issue_code,
            title=c.title,
            status=str(c.status.value if hasattr(c.status, "value") else c.status),
        ).model_dump(mode="json")
        for c in children
    ]

    # 如果有关联项目，查询项目信息
    if issue.project_id:
        result = await db.execute(
            select(Project).where(Project.id == issue.project_id)
        )
        project = result.scalar_one_or_none()
        if project:
            from opentask.models.issue.schema import ProjectInfo
            issue_dict["project"] = ProjectInfo(
                id=project.id,
                name=project.name,
                description=project.description
            ).model_dump(mode='json', exclude_none=False)

    return {
        "code": 200,
        "message": "success",
        "data": issue_dict,
        "timestamp": 0,
    }


@router.put("/{issue_id}")
async def update_issue(
    issue_id: str,
    data: IssueUpdate,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """更新 Issue（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)

    try:
        issue = await service.update_issue(issue_id, data, str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not issue:
        raise HTTPException(status_code=404, detail="Issue 不存在")

    return {
        "code": 200,
        "message": "Issue 更新成功",
        "data": IssueResponse.model_validate(issue),
        "timestamp": 0,
    }


@router.delete("/{issue_id}")
async def delete_issue(
    issue_id: str,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """删除 Issue（软删除；E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)

    success = await service.delete_issue(issue_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Issue 不存在")

    return {
        "code": 200,
        "message": "Issue 删除成功",
        "data": None,
        "timestamp": 0,
    }


# ========================================================================
# 批量操作
# ========================================================================

@router.post("/bulk/update")
async def bulk_update_issues(
    data: IssueBulkUpdate,
    service: IssueService = Depends(get_issue_service),
    ctx: tuple = Depends(require_workspace_context),
):
    """批量更新 Issue（E20：强制 X-Workspace-Id + 本 WS 过滤）"""
    ws, _member, user = ctx
    try:
        affected_rows = await service.bulk_update_issues(
            data, str(user.id), workspace_id=ws.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "code": 200,
        "message": f"成功更新 {affected_rows} 个 Issue",
        "data": {"affected_rows": affected_rows},
        "timestamp": 0,
    }


@router.post("/bulk/delete")
async def bulk_delete_issues(
    data: IssueBulkDelete,
    service: IssueService = Depends(get_issue_service),
    ctx: tuple = Depends(require_workspace_context),
):
    """批量删除 Issue（软删除；E20：强制本 WS）"""
    ws, _member, user = ctx
    # 仅删除本工作区可见 ID
    from sqlalchemy import select as sa_select
    from opentask.models.issue.model import Issue as IssueModel

    allowed_q = await service.db.execute(
        sa_select(IssueModel.id).where(
            IssueModel.id.in_(data.issue_ids),
            IssueModel.workspace_id == ws.id,
            IssueModel.is_deleted == False,  # noqa: E712
        )
    )
    allowed_ids = [row[0] for row in allowed_q.all()]
    if not allowed_ids:
        raise HTTPException(status_code=403, detail="无权批量删除这些 Issue")
    affected_rows = await service.bulk_delete_issues(allowed_ids, str(user.id))

    return {
        "code": 200,
        "message": f"成功删除 {affected_rows} 个 Issue",
        "data": {"affected_rows": affected_rows},
        "timestamp": 0,
    }


# ========================================================================
# 评论操作
# ========================================================================

@router.get("/{issue_id}/comments")
async def get_comments(
    issue_id: str,
    service: IssueService = Depends(get_issue_service),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(authenticate),
):
    """获取 Issue 的所有评论（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    comments = await service.get_comments(issue_id)

    # 收集所有唯一的 user_id
    user_ids = list(set([UUID(c.user_id) for c in comments if c.user_id]))

    # 批量查询用户信息
    user_info_map = {}
    if user_ids:
        result = await db.execute(
            select(UserModel).where(UserModel.id.in_(user_ids))
        )
        users = result.scalars().all()
        user_info_map = {
            str(user.id): UserInfo(
                id=str(user.id),
                name=user.name,
                sso_name=getattr(user, 'sso_name', None),
                sso_account=getattr(user, 'sso_account', None)
            )
            for user in users
        }

    # E27：批量加载评论反应
    reaction_maps = await service.get_comments_reaction_maps([c.id for c in comments])

    # 构建响应，添加用户信息 + reactions
    # 注意：ORM 上也有 reactions 关系，勿 model_validate(ORM) 以免懒加载
    rows = []
    for comment in comments:
        raw = {
            "id": comment.id,
            "issue_id": comment.issue_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "parent_id": comment.parent_id,
            "comment_type": comment.comment_type,
            "meta_data": comment.meta_data,
            "is_deleted": comment.is_deleted,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
        }
        comment_dict = IssueCommentResponse.model_validate(raw).model_dump()
        if comment.user_id and str(comment.user_id) in user_info_map:
            comment_dict["user_info"] = user_info_map[str(comment.user_id)]
        comment_dict["reactions"] = reaction_maps.get(comment.id, {})
        rows.append(IssueCommentResponse(**comment_dict))

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": rows,
            "total": len(rows),
        },
        "timestamp": 0,
    }


@router.post("/{issue_id}/comments")
async def add_comment(
    issue_id: str,
    data: IssueCommentRequest,
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
    db: AsyncSession = Depends(get_session),
):
    """添加评论（支持 /task_create 命令）

    限制：
    - content: 1-500 字符
    """
    await _require_issue_access(issue_id, service=service, user=current_user)
    user_id = str(current_user.id)
    content = data.content

    # 验证内容长度
    if len(content) > 500:
        raise HTTPException(
            status_code=422,
            detail=f"评论内容过长，最大允许500字符，当前{len(content)}字符"
        )

    # 检查是否为 /task_create 命令
    if content.strip().startswith("/task_create"):
        return await handle_task_create_command(
            issue_id=issue_id,
            command=content,
            user_id=user_id,
            db=db
        )

    try:
        comment = await service.add_comment(
            issue_id=issue_id,
            content=content,
            user_id=user_id,
            parent_id=data.parent_id,
        )

        # 手动构造响应，避免枚举序列化问题
        return {
            "code": 200,
            "message": "评论添加成功",
            "data": {
                "id": comment.id,
                "issue_id": comment.issue_id,
                "user_id": comment.user_id,
                "content": comment.content,
                "parent_id": comment.parent_id,
                "comment_type": comment.comment_type.value if hasattr(comment.comment_type, 'value') else str(comment.comment_type),
                "meta_data": comment.meta_data,
                "is_deleted": comment.is_deleted,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
            },
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"添加评论失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/comments/{comment_id}")
async def update_comment(
    comment_id: str,
    comment_data: IssueCommentUpdate,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """更新评论

    限制：
    - content: 1-500 字符
    """
    await _require_comment_issue_access(comment_id, service=service, user=current_user)
    if not comment_data.content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")

    # 验证内容长度
    if len(comment_data.content) > 500:
        raise HTTPException(
            status_code=422,
            detail=f"评论内容过长，最大允许500字符，当前{len(comment_data.content)}字符"
        )

    comment = await service.update_comment(comment_id, comment_data.content, str(current_user.id))
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在或无权限修改")

    return {
        "code": 200,
        "message": "评论更新成功",
        "data": IssueCommentResponse.model_validate(comment),
        "timestamp": 0,
    }


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """删除评论（软删除；E15：成员校验）"""
    await _require_comment_issue_access(comment_id, service=service, user=current_user)
    success = await service.delete_comment(comment_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="评论不存在或无权限删除")

    return {
        "code": 200,
        "message": "评论删除成功",
        "data": None,
        "timestamp": 0,
    }



@router.get("/{issue_id}/children")
async def get_issue_children(
    issue_id: str,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """列出 Issue 的直接子项（depth-1 摘要；E15：成员校验）"""
    issue = await _require_issue_access(issue_id, service=service, user=current_user)
    children = await service.list_child_issues(issue_id)
    rows = [
        IssueChildSummary(
            id=c.id,
            issue_code=c.issue_code,
            title=c.title,
            status=str(c.status.value if hasattr(c.status, "value") else c.status),
        )
        for c in children
    ]
    return {
        "code": 200,
        "message": "success",
        "data": {"rows": rows, "total": len(rows)},
        "timestamp": 0,
    }


# ========================================================================
# 关系操作
# ========================================================================

@router.get("/{issue_id}/relations")
async def get_relations(
    issue_id: str,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """获取 Issue 的所有关系（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    source_relations, target_relations = await service.get_relations(issue_id)

    source_rows = [IssueRelationResponse.model_validate(r) for r in source_relations]
    target_rows = [IssueRelationResponse.model_validate(r) for r in target_relations]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "as_source": source_rows,
            "as_target": target_rows,
        },
        "timestamp": 0,
    }


@router.post("/{issue_id}/relations")
async def add_relation(
    issue_id: str,
    target_id: str = Query(..., description="目标 Issue ID"),
    relation_type: RelationType = Query(..., description="关系类型"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """添加 Issue 关系（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    try:
        relation = await service.add_relation(
            source_id=issue_id,
            target_id=target_id,
            relation_type=relation_type,
            user_id=str(current_user.id),
        )
        return {
            "code": 200,
            "message": "关系添加成功",
            "data": IssueRelationResponse.model_validate(relation),
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"添加关系失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{issue_id}/relations")
async def remove_relation(
    issue_id: str,
    target_id: str = Query(..., description="目标 Issue ID"),
    relation_type: RelationType = Query(..., description="关系类型"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """移除 Issue 关系（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    success = await service.remove_relation(
        source_id=issue_id,
        target_id=target_id,
        relation_type=relation_type,
    )

    if not success:
        raise HTTPException(status_code=404, detail="关系不存在")

    return {
        "code": 200,
        "message": "关系移除成功",
        "data": None,
        "timestamp": 0,
    }


# ========================================================================
# 标签操作
# ========================================================================

class IssueTagsReplace(BaseModel):
    tag_ids: List[int] = Field(default_factory=list)


@router.get("/{issue_id}/tags")
async def get_tags(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """获取 Issue 的所有标签"""
    ws, _member, _user = ctx
    rows = await TagService(session).list_issue_tags(issue_id, workspace_id=ws.id)
    briefs = [serialize_tag_brief(t) for t in rows]
    return {
        "code": 200,
        "message": "success",
        "data": {"rows": briefs, "total": len(briefs)},
        "timestamp": 0,
    }


@router.put("/{issue_id}/tags")
async def replace_tags(
    issue_id: str,
    body: IssueTagsReplace,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """整体替换 Issue 标签（L picker）"""
    ws, member, user = ctx
    require_tag_writer(member)
    rows = await TagService(session).replace_issue_tags(
        issue_id=issue_id,
        tag_ids=body.tag_ids,
        workspace_id=ws.id,
        user_id=str(user.id),
    )
    briefs = [serialize_tag_brief(t) for t in rows]
    return {
        "code": 200,
        "message": "标签已更新",
        "data": {"rows": briefs, "total": len(briefs)},
        "timestamp": 0,
    }


@router.post("/{issue_id}/tags/{tag_id}")
async def add_tag(
    issue_id: str,
    tag_id: int,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """添加标签到 Issue"""
    ws, member, user = ctx
    require_tag_writer(member)
    tag = await TagService(session).attach_tag(
        issue_id=issue_id,
        tag_id=tag_id,
        workspace_id=ws.id,
        user_id=str(user.id),
    )
    return {
        "code": 200,
        "message": "标签添加成功",
        "data": {"tag": serialize_tag_brief(tag)},
        "timestamp": 0,
    }


@router.delete("/{issue_id}/tags/{tag_id}")
async def remove_tag(
    issue_id: str,
    tag_id: int,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """从 Issue 移除标签"""
    ws, member, user = ctx
    require_tag_writer(member)
    await TagService(session).detach_tag(
        issue_id=issue_id,
        tag_id=tag_id,
        workspace_id=ws.id,
        user_id=str(user.id),
    )
    return {
        "code": 200,
        "message": "标签移除成功",
        "data": None,
        "timestamp": 0,
    }




# ========================================================================
# Custom Fields (E25)
# ========================================================================

class IssueCustomFieldsPatch(BaseModel):
    values: list[dict] = Field(default_factory=list, description="[{fieldId|key, value}]")


@router.patch("/{issue_id}/custom-fields")
async def patch_issue_custom_fields(
    issue_id: str,
    body: IssueCustomFieldsPatch,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
    service: IssueService = Depends(get_issue_service),
):
    """批量 upsert Issue 自定义字段取值（value=null 清除）"""
    ws, member, user = ctx
    require_cf_writer(member)
    issue = await _require_issue_access(issue_id, service=service, user=user)
    if issue.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="Issue 不存在")
    rows = await CustomFieldService(session).upsert_issue_values(
        workspace_id=ws.id,
        issue_id=issue.id,
        entries=list(body.values or []),
    )
    return {
        "code": 200,
        "message": "自定义字段已更新",
        "data": {"customFields": rows},
        "timestamp": 0,
    }


# ========================================================================
# 评论反应（E27）
# ========================================================================

@router.get("/{issue_id}/comments/{comment_id}/reactions")
async def get_comment_reactions(
    issue_id: str,
    comment_id: str,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """获取评论反应映射 emoji → userId[]"""
    comment = await _require_comment_issue_access(
        comment_id, service=service, user=current_user
    )
    if comment.issue_id != issue_id:
        raise HTTPException(status_code=404, detail="评论不存在")
    mapping = await service.get_comment_reaction_map(comment_id)
    return {
        "code": 200,
        "message": "success",
        "data": {"reactions": mapping},
        "timestamp": 0,
    }


@router.post("/{issue_id}/comments/{comment_id}/reactions")
async def add_comment_reaction(
    issue_id: str,
    comment_id: str,
    data: IssueReactionCreate,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    comment = await _require_comment_issue_access(
        comment_id, service=service, user=current_user
    )
    if comment.issue_id != issue_id:
        raise HTTPException(status_code=404, detail="评论不存在")
    reaction = await service.add_comment_reaction(
        comment_id, data.emoji, str(current_user.id)
    )
    return {
        "code": 200,
        "message": "反应添加成功",
        "data": {
            "reaction_id": reaction.id,
            "reactions": await service.get_comment_reaction_map(comment_id),
        },
        "timestamp": 0,
    }


@router.delete("/{issue_id}/comments/{comment_id}/reactions")
async def remove_comment_reaction(
    issue_id: str,
    comment_id: str,
    emoji: str = Query(..., description="表情符号"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    comment = await _require_comment_issue_access(
        comment_id, service=service, user=current_user
    )
    if comment.issue_id != issue_id:
        raise HTTPException(status_code=404, detail="评论不存在")
    success = await service.remove_comment_reaction(
        comment_id, emoji, str(current_user.id)
    )
    if not success:
        raise HTTPException(status_code=404, detail="反应不存在")
    return {
        "code": 200,
        "message": "反应移除成功",
        "data": {"reactions": await service.get_comment_reaction_map(comment_id)},
        "timestamp": 0,
    }


# ========================================================================
# 反应操作
# ========================================================================

@router.get("/{issue_id}/reactions")
async def get_reactions(
    issue_id: str,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """获取 Issue 的所有反应（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    stats = await service.get_reaction_stats(issue_id)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": list(stats.values()),
            "total": len(stats),
        },
        "timestamp": 0,
    }


@router.post("/{issue_id}/reactions")
async def add_reaction(
    issue_id: str,
    data: IssueReactionCreate,
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """添加反应（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    logger.info(f"DEBUG: add_reaction called, user_id={current_user.id}")
    user_id = str(current_user.id)

    try:
        reaction = await service.add_reaction(issue_id, data.emoji, user_id)
        return {
            "code": 200,
            "message": "反应添加成功",
            "data": {"reaction_id": reaction.id},
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"添加反应失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{issue_id}/reactions")
async def remove_reaction(
    issue_id: str,
    emoji: str = Query(..., description="表情符号"),
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """移除反应（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    user_id = str(current_user.id)

    try:
        success = await service.remove_reaction(issue_id, emoji, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="反应不存在")

        return {
            "code": 200,
            "message": "反应移除成功",
            "data": None,
            "timestamp": 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除反应失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================================================
# 时间线操作
# ========================================================================

@router.get("/{issue_id}/timeline")
async def get_timeline(
    issue_id: str,
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    service: IssueService = Depends(get_issue_service),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(authenticate),
):
    """获取 Issue 时间线（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    timeline = await service.get_timeline(issue_id, limit)

    # 收集所有唯一的 user_id
    user_ids = list(set([UUID(t.user_id) for t in timeline if t.user_id]))

    # 批量查询用户信息
    user_info_map = {}
    if user_ids:
        result = await db.execute(
            select(UserModel).where(UserModel.id.in_(user_ids))
        )
        users = result.scalars().all()
        user_info_map = {
            str(user.id): UserInfo(
                id=str(user.id),
                name=user.name,
                sso_name=getattr(user, 'sso_name', None),
                sso_account=getattr(user, 'sso_account', None)
            )
            for user in users
        }

    # 构建响应，添加用户信息
    rows = []
    for t in timeline:
        timeline_dict = IssueTimelineResponse.model_validate(t).model_dump()
        if t.user_id and str(t.user_id) in user_info_map:
            timeline_dict["user_info"] = user_info_map[str(t.user_id)]
        rows.append(IssueTimelineResponse(**timeline_dict))

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": rows,
            "total": len(rows),
        },
        "timestamp": 0,
    }


# ========================================================================
# 统计操作
# ========================================================================

# ========================================================================
# 快速状态变更
# ========================================================================

@router.put("/{issue_id}/status")
async def update_status(
    issue_id: str,
    status: str = Query(..., description="新状态"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """快速更新 Issue 状态"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    update_data = IssueUpdate(status=status)  # type: ignore
    issue = await service.update_issue(issue_id, update_data, str(current_user.id))

    if not issue:
        raise HTTPException(status_code=404, detail="Issue 不存在")

    return {
        "code": 200,
        "message": "状态更新成功",
        "data": IssueResponse.model_validate(issue),
        "timestamp": 0,
    }


@router.put("/{issue_id}/assignee")
async def update_assignee(
    issue_id: str,
    assignee_id: Optional[str] = Query(None, description="负责人 ID"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """快速更新 Issue 负责人"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    update_data = IssueUpdate(assignee_id=assignee_id)
    issue = await service.update_issue(issue_id, update_data, str(current_user.id))

    if not issue:
        raise HTTPException(status_code=404, detail="Issue 不存在")

    return {
        "code": 200,
        "message": "负责人更新成功",
        "data": IssueResponse.model_validate(issue),
        "timestamp": 0,
    }


@router.put("/{issue_id}/priority")
async def update_priority(
    issue_id: str,
    priority: str = Query(..., description="新优先级"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """快速更新 Issue 优先级"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    update_data = IssueUpdate(priority=priority)  # type: ignore
    issue = await service.update_issue(issue_id, update_data, str(current_user.id))

    if not issue:
        raise HTTPException(status_code=404, detail="Issue 不存在")

    return {
        "code": 200,
        "message": "优先级更新成功",
        "data": IssueResponse.model_validate(issue),
        "timestamp": 0,
    }


@router.put("/{issue_id}/reporter")
async def update_reporter(
    issue_id: str,
    reporter_id: Optional[str] = Query(None, description="报告人 ID"),
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """快速更新 Issue 报告人"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    update_data = IssueUpdate(reporter_id=reporter_id)
    issue = await service.update_issue(issue_id, update_data, str(current_user.id))

    if not issue:
        raise HTTPException(status_code=404, detail="Issue 不存在")

    return {
        "code": 200,
        "message": "报告人更新成功",
        "data": IssueResponse.model_validate(issue),
        "timestamp": 0,
    }


# ============================================================================
# 附件操作
# ============================================================================

@router.get("/{issue_id}/attachments")
async def get_issue_attachments(
    issue_id: str,
    service: IssueService = Depends(get_issue_service),
    current_user: UserModel = Depends(authenticate),
):
    """获取 Issue 的所有附件。空列表必须 200（E11-S4）。E15：成员校验。"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    try:
        attachments = await service.get_attachments(issue_id)
    except Exception as e:
        # 防御：缺表/瞬时 DB 错误时不把详情页打成 500 刷屏
        logger.exception("get_issue_attachments failed for %s: %s", issue_id, e)
        return {
            "code": 200,
            "message": "success",
            "data": [],
            "timestamp": 0,
        }

    rows = []
    for att in attachments:
        rows.append({
            "id": att.id,
            "entity_type": att.entity_type,
            "entity_id": att.entity_id,
            "file_path": att.file_path,
            "file_name": att.file_name,
            "file_type": att.file_type,
            "file_size": att.file_size,
            "status": att.status.value if hasattr(att.status, 'value') else str(att.status),
            "created_at": att.created_at.isoformat() if att.created_at else None,
            "updated_at": att.updated_at.isoformat() if att.updated_at else None,
            "created_by": att.created_by,
            "updated_by": att.updated_by,
        })

    return {
        "code": 200,
        "message": "success",
        "data": rows,
        "timestamp": 0,
    }


@router.post("/{issue_id}/attachments")
async def upload_issue_attachment(
    issue_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """上传附件到 Issue（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    user_id = str(current_user.id)

    try:
        # 使用存储服务保存文件
        storage_service = get_storage_service()
        file_path, original_filename, file_size = await storage_service.save_upload_file(
            upload_file=file,
            subdir=f"issues/{issue_id}"
        )

        # 获取文件 MIME 类型
        file_type = file.content_type or "application/octet-stream"

        # 部门归属快照：取上传人主部门
        dept_id = await RbacService(service.db).get_primary_dept_id(current_user)

        # 创建附件记录
        attachment = await service.add_attachment(
            issue_id=issue_id,
            file_path=file_path,
            file_name=original_filename,
            file_type=file_type,
            file_size=file_size,
            user_id=user_id,
            dept_id=dept_id,
        )

        return {
            "code": 200,
            "message": "附件上传成功",
            "data": {
                "id": attachment.id,
                "file_name": attachment.file_name,
                "file_type": attachment.file_type,
                "file_size": attachment.file_size,
                "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
            },
            "timestamp": 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"上传附件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{issue_id}/attachments/{attachment_id}")
async def delete_issue_attachment(
    issue_id: str,
    attachment_id: str,
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """删除 Issue 附件（E15：成员校验）"""
    await _require_issue_access(issue_id, service=service, user=current_user)
    user_id = str(current_user.id)

    success = await service.delete_attachment(issue_id, attachment_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="附件不存在")

    return {
        "code": 200,
        "message": "附件删除成功",
        "data": None,
        "timestamp": 0,
    }


@router.get("/{issue_id}/attachments/{attachment_id}/download")
async def download_issue_attachment(
    issue_id: str,
    attachment_id: str,
    service: IssueService = Depends(get_issue_service),
):
    """下载 Issue 附件"""
    attachment = await service.get_attachment(issue_id, attachment_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    storage_service = get_storage_service()

    try:
        file_stream = storage_service.get_file_stream(attachment.file_path)

        def iter_file():
            """生成器函数：分块读取文件数据"""
            chunk_size = 8192  # 8KB chunks
            while True:
                data = file_stream.read(chunk_size)
                if not data:
                    break
                yield data
            file_stream.close()

        # 使用RFC 5987编码支持中文文件名
        encoded_filename = quote(attachment.file_name)
        return StreamingResponse(
            iter_file(),
            media_type=attachment.file_type,
            headers={
                "Content-Disposition": f'attachment; filename*=UTF-8\'\'{encoded_filename}'
            }
        )
    except Exception as e:
        import traceback
        logger.error(f"MinIO 文件读取失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"文件读取失败: {str(e)}")


# ========================================================================
# 临时测试端点（无需认证）
# ========================================================================

@router.post("/debug/simple-test")
async def debug_simple_test(request: Request):
    """最简单的测试：直接读取请求体"""
    import json

    body = await request.body()
    body_str = body.decode('utf-8')

    try:
        data = json.loads(body_str)
        return {
            "success": True,
            "received_data": data,
            "body_str": body_str
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "body_str": body_str
        }


@router.post("/debug/raw-test")
async def debug_raw_test(request: Request):
    """最简单的测试：直接读取原始请求体"""
    import json

    # 读取原始请求体
    body = await request.body()
    body_str = body.decode('utf-8')

    try:
        body_json = json.loads(body_str)
    except:
        body_json = None

    return {
        "raw_body": body_str,
        "parsed_json": body_json,
        "content_type": request.headers.get("content-type"),
        "message": "Raw body received!"
    }


@router.post("/debug/body-test")
async def debug_body_test(
    content: str = Body(..., embed=True)
):
    """调试：测试 Body 参数是否工作"""
    return {
        "received": content,
        "message": "Body parameter works!"
    }


@router.post("/debug/new-comment-endpoint")
async def debug_new_comment(
    issue_id: str = Body(..., embed=True),
    content: str = Body(..., embed=True),
    service: IssueService = Depends(get_issue_service),
):
    """全新的评论端点测试"""
    try:
        comment = await service.add_comment(
            issue_id=issue_id,
            content=content,
            user_id="debug_test",
            parent_id=None,
        )
        return {
            "code": 200,
            "message": "评论添加成功（新端点）",
            "data": IssueCommentResponse.model_validate(comment),
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"[NEW ENDPOINT] 添加评论失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/{issue_id}/comments")
async def test_add_comment(
    issue_id: str,
    comment_data: dict = Body(...),
    service: IssueService = Depends(get_issue_service),
):
    """测试添加评论（无需认证）"""
    user_id = "system"

    try:
        logger.info(f"[TEST] 收到评论请求: issue_id={issue_id}, raw_data={comment_data}")

        content = comment_data.get("content", "")
        parent_id = comment_data.get("parent_id")

        if not content:
            raise HTTPException(status_code=400, detail="评论内容不能为空")

        comment = await service.add_comment(
            issue_id=issue_id,
            content=content,
            user_id=user_id,
            parent_id=parent_id,
        )

        logger.info(f"[TEST] 评论创建成功: id={comment.id}, content={comment.content[:20]}...")

        return {
            "code": 200,
            "message": "评论添加成功",
            "data": IssueCommentResponse.model_validate(comment),
            "timestamp": 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEST] 添加评论失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========================================================================
# /task_create 命令处理
# ========================================================================

async def handle_task_create_command(
    issue_id: str,
    command: str,
    user_id: str,
    db: AsyncSession
):
    """处理 /task_create 命令，创建任务到 mission_center"""
    from opentask.services.mission_center.service import get_task_service, TaskPriority
    from opentask.models.issue.model import Issue
    from sqlalchemy import select
    import uuid
    from datetime import datetime

    # 解析命令：/task_create 标题 [描述]
    parts = command.strip().split(maxsplit=2)
    if len(parts) < 2:
        raise HTTPException(
            status_code=400,
            detail="命令格式错误。正确格式: /task_create 标题 [描述]"
        )

    title = parts[1].strip()
    description = parts[2].strip() if len(parts) > 2 else ""

    # 获取 issue 信息，用于上下文
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id)
    )
    issue = result.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=404, detail="Issue 不存在")

    # 调用 mission_center service 创建任务
    try:
        task_service = get_task_service()

        # 构造任务描述
        full_description = description + f"\n\n来源 Issue: {issue.issue_code}\n标题: {issue.title}" if description else f"来源 Issue: {issue.issue_code}\n标题: {issue.title}"

        # 直接调用 service 层创建任务
        # 部门归属快照：优先继承所属 Issue 的 dept_id（任务的部门跟随所属 Issue，
        # Issue 部门缺失时回退评论人主部门，均无则保持 NULL）
        dept_id = issue.dept_id
        if dept_id is None:
            commenter = (
                await db.execute(select(UserModel).where(UserModel.id == user_id))
            ).scalar_one_or_none()
            if commenter is not None:
                dept_id = await RbacService(db).get_primary_dept_id(commenter)

        task = await task_service.create_task(
            title=f"[{issue.issue_code}] {title}",
            description=full_description,
            priority=TaskPriority.MEDIUM,
            metadata={
                "source_issue_id": issue_id,
                "source_issue_code": issue.issue_code,
                "created_by_user": user_id
            },
            dept_id=dept_id,
        )

        # 返回任务创建结果
        task_id = task.task_id
        comment_content = f"✅ 任务已创建\n任务ID: {task_id}\n标题: {title}"

        # 添加系统评论记录
        from opentask.models.issue.model import IssueComment

        comment = IssueComment(
            id=str(uuid.uuid4()),
            issue_id=issue_id,
            content=comment_content,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            comment_type="system"
        )

        db.add(comment)
        await db.commit()

        return {
            "code": 200,
            "message": "任务创建成功",
            "data": {
                "task_created": True,
                "task_id": task_id,
                "comment_content": comment_content,
                "task": task.to_dict()
            },
            "timestamp": 0,
        }

    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"任务创建失败: {str(e)}"
        )


# ============================================================================
# Issue Watchers (E18)
# ============================================================================

watchers_router = APIRouter(prefix="/{issue_id}/watchers", tags=["Issue Watchers"])


@watchers_router.get("")
async def list_issue_watchers(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    from opentask.services.issue_watcher.service import (
        IssueWatcherService,
        enrich_watchers,
    )

    ws, _member, _user = ctx
    rows = await IssueWatcherService(db).list(issue_id=issue_id, workspace_id=ws.id)
    return {
        "code": 200,
        "message": "success",
        "data": await enrich_watchers(db, rows),

        "timestamp": 0,
    }


@watchers_router.post("")
async def watch_issue(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    from opentask.services.issue_watcher.service import (
        IssueWatcherService,
        serialize_watcher,
    )

    ws, _member, user = ctx
    row = await IssueWatcherService(db).watch(
        issue_id=issue_id, workspace_id=ws.id, user_id=str(user.id)
    )
    return {
        "code": 200,
        "message": "已关注",
        "data": serialize_watcher(row),
        "timestamp": 0,
    }


@watchers_router.delete("")
async def unwatch_issue(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    from opentask.services.issue_watcher.service import IssueWatcherService

    ws, _member, user = ctx
    await IssueWatcherService(db).unwatch(
        issue_id=issue_id, workspace_id=ws.id, user_id=str(user.id)
    )
    return {
        "code": 200,
        "message": "已取消关注",
        "data": None,
        "timestamp": 0,
    }


router.include_router(watchers_router)
