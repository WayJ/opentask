"""Jira 线格式路由（/rest/api/2/*，探测报告 §2/§3 的完整调用面）

挂在 tasks 契约路由内（见 tasks/__init__.py 的 Mount）——app.py 不属于本
sprint 允许路径，且 Jira 层与 /tasks 契约层共用 mapping/auth/schemas 内核，
宿主关系一致。读写全部经 ContractIssueService / IssueService（与 UI 侧同权
限路径），本层只做线格式转换。

成功写操作按 Orca 期望返回 204 无 body（Ur：204 → null）。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.tasks.mapping import (
    generic_status_to_issue,
    get_forbidden_operations,
    get_generic_statuses,
    issue_status_to_generic,
)
from opentask.api.tasks.service import ContractIssueService, sync_issue_labels
from opentask.models.issue.enums import IssuePriority, IssueType
from opentask.models.issue.model import Issue, IssueComment
from opentask.models.issue.schema import IssueCreate, IssueUpdate
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.services.issue_service import IssueService

from .auth import authenticate_jira, get_jira_session
from .converters import (
    PROJECT_OBJECT,
    available_transitions,
    display_name,
    issue_to_jira,
    issue_type_catalog,
    jira_timestamp,
    priority_catalog,
    user_object,
)
from .errors import (
    FORBIDDEN_OP_BY_ROUTE,
    jira_bad_request,
    jira_forbidden,
    jira_not_found,
    jira_status_unknown,
)
from .jql import JqlFilter, translate_jql
from .keys import issue_code_to_key, key_to_issue_code

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Jira 线格式 (Jira Wire Compatibility)"])

# 搜索分页（探测 §3：Orca vVt 客户端钳 1..100，缺省 30；服务端 50 兜底）
SEARCH_MAX_LIMIT = 100


# ============================================================================
# 内部辅助
# ============================================================================


async def get_jira_service(
    db: AsyncSession = Depends(get_jira_session),
) -> ContractIssueService:
    return ContractIssueService(db)


def _ensure_allowed(route_key: str) -> None:
    """禁操作校验：与 /tasks 契约共用 contract.forbidden_operations 语义"""
    operation = FORBIDDEN_OP_BY_ROUTE[route_key]
    if operation in get_forbidden_operations():
        raise jira_forbidden(
            f"操作 {operation} 已被禁用（contract.forbidden_operations）"
        )


async def _load_user_map(
    db: AsyncSession, issues: List[Issue]
) -> Dict[str, UserModel]:
    """批量预取 assignee/reporter 的用户对象（搜索列表用）"""
    ids = {i.assignee_id for i in issues if i.assignee_id} | {
        i.reporter_id for i in issues if i.reporter_id
    }
    if not ids:
        return {}
    result = await db.execute(select(UserModel).where(UserModel.id.in_(list(ids))))
    return {str(u.id): u for u in result.scalars().all()}


async def _issue_payload(db: AsyncSession, issue: Issue) -> Dict[str, Any]:
    """Issue → Jira issue JSON（tags 名称与用户对象就地补齐）"""
    tag_ids = [it.tag_id for it in issue.tags]
    tag_names: Dict[int, str] = {}
    if tag_ids:
        result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        tag_names = {t.id: t.name for t in result.scalars().all()}
    return issue_to_jira(
        issue,
        tag_names_by_id=tag_names,
        assignee=issue.assignee,
        reporter=issue.reporter,
    )


async def _issues_payload(db: AsyncSession, issues: List[Issue]) -> List[Dict]:
    tag_ids = {it.tag_id for issue in issues for it in issue.tags}
    tag_names: Dict[int, str] = {}
    if tag_ids:
        result = await db.execute(select(Tag).where(Tag.id.in_(list(tag_ids))))
        tag_names = {t.id: t.name for t in result.scalars().all()}
    user_map = await _load_user_map(db, issues)
    return [
        issue_to_jira(
            issue,
            tag_names_by_id=tag_names,
            assignee=user_map.get(issue.assignee_id) if issue.assignee_id else None,
            reporter=user_map.get(issue.reporter_id) if issue.reporter_id else None,
        )
        for issue in issues
    ]


async def _resolve_issue(service: ContractIssueService, key: str) -> Issue:
    """Jira key → Issue（404 带 CONTRACT_TASK_NOT_FOUND 码）"""
    try:
        code = key_to_issue_code(key)
    except ValueError as e:
        raise jira_not_found(f"无法识别的 key {key!r}（{e}）") from e
    issue = await service.get_issue(code, by_code=True)
    if issue is None:
        raise jira_not_found(f"任务不存在: {key}")
    return issue


async def _resolve_user_ref(
    db: AsyncSession, ref: Optional[str]
) -> Optional[UserModel]:
    """assignee 引用（用户 ID 精确 / 用户名 ci）→ UserModel；未命中 None"""
    if not ref:
        return None
    result = await db.execute(select(UserModel).where(UserModel.id == ref))
    user = result.scalar_one_or_none()
    if user is not None:
        return user
    result = await db.execute(
        select(UserModel).where(UserModel.username == ref)
    )
    return result.scalar_one_or_none()


async def _apply_jql_parties(
    jql_filter: JqlFilter, current_user: UserModel, db: AsyncSession
) -> JqlFilter:
    """currentUser()/用户名引用解析为 assignee_id/reporter_id；未命中 → 空集"""
    if jql_filter.assignee_is_current:
        jql_filter.assignee_ref = str(current_user.id)
        jql_filter.assignee_is_current = False
    elif jql_filter.assignee_ref is not None:
        user = await _resolve_user_ref(db, jql_filter.assignee_ref)
        if user is None:
            jql_filter.forced_empty = True
        else:
            jql_filter.assignee_ref = str(user.id)
    if jql_filter.reporter_is_current:
        jql_filter.reporter_ref = str(current_user.id)
        jql_filter.reporter_is_current = False
    elif jql_filter.reporter_ref is not None:
        user = await _resolve_user_ref(db, jql_filter.reporter_ref)
        if user is None:
            jql_filter.forced_empty = True
        else:
            jql_filter.reporter_ref = str(user.id)

    # project 子句：值集合里没有 OPENTASK（ci）→ 空集
    if jql_filter.project_values and not any(
        (v or "").strip().upper() == "OPENTASK" for v in jql_filter.project_values
    ):
        jql_filter.forced_empty = True
    return jql_filter


# ============================================================================
# 会话/身份（连接验证的第一跳，探测 §5）
# ============================================================================


@router.get("/myself")
async def myself(
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    payload = user_object(current_user) or {}
    payload.pop("accountId", None)  # server 模式以 name/key 为主（H4 读法兼容）
    payload["timeZone"] = "UTC"
    payload["locale"] = "zh_CN"
    return payload


# ============================================================================
# 搜索（list / search 两命令的公共底层，探测 §3）
# ============================================================================


@router.post("/search")
async def search(
    payload: Dict[str, Any] = Body(...),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    _ensure_allowed("search")
    jql = payload.get("jql") or ""
    max_results = payload.get("maxResults") or 50
    start_at = payload.get("startAt") or 0
    try:
        max_results = max(1, min(int(max_results), SEARCH_MAX_LIMIT))
        start_at = max(0, int(start_at))
    except (TypeError, ValueError):
        raise jira_bad_request("maxResults/startAt 必须是整数")

    jql_filter = await _apply_jql_parties(translate_jql(jql), current_user, service.db)

    issues: List[Issue] = []
    total = 0
    if not jql_filter.forced_empty:
        issues, total = await service.list_issues_for_contract(
            status=jql_filter.statuses,
            assignee_id=jql_filter.assignee_ref,
            reporter_id=jql_filter.reporter_ref,
            issue_codes=jql_filter.issue_codes,
            title_kw=jql_filter.title_kw,
            desc_kw=jql_filter.desc_kw,
            any_kws=jql_filter.any_kws or None,
            limit=max_results,
            offset=start_at,
            order=jql_filter.order,
        )

    return {
        "expand": "schema,names",
        "startAt": start_at,
        "maxResults": max_results,
        "total": total,
        "issues": await _issues_payload(service.db, issues),
    }


# ============================================================================
# 元数据（project / issuetype / create fields / priority / field / filter）
# ============================================================================


@router.get("/project")
async def list_projects(
    current_user: UserModel = Depends(authenticate_jira),
) -> List[Dict[str, Any]]:
    return [dict(PROJECT_OBJECT)]


@router.get("/issue/createmeta/{project_key}/issuetypes")
async def createmeta_issue_types(
    project_key: str,
    startAt: int = Query(0, ge=0),
    maxResults: int = Query(50, ge=1, le=100),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    values = issue_type_catalog()
    return {
        "expand": "projects",
        "startAt": startAt,
        "maxResults": maxResults,
        "total": len(values),
        "values": values[startAt : startAt + maxResults],
    }


@router.get("/issue/createmeta/{project_key}/issuetypes/{type_id}")
async def createmeta_create_fields(
    project_key: str,
    type_id: str,
    startAt: int = Query(0, ge=0),
    maxResults: int = Query(100, ge=1, le=100),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    valid_ids = {t.value for t in IssueType}
    if type_id not in valid_ids:
        raise jira_not_found(f"issue type 不存在: {type_id}")
    values = _create_field_catalog()
    return {
        "expand": "projects",
        "startAt": startAt,
        "maxResults": maxResults,
        "total": len(values),
        "values": values[startAt : startAt + maxResults],
    }


def _create_field_catalog() -> List[Dict[str, Any]]:
    """create 字段元数据（pBt 读 key/fieldId/name/required/schema/allowedValues）"""
    return [
        {
            "fieldId": "summary",
            "key": "summary",
            "name": "Summary",
            "required": True,
            "schema": {"type": "string"},
        },
        {
            "fieldId": "description",
            "key": "description",
            "name": "Description",
            "required": False,
            "schema": {"type": "string"},
        },
        {
            "fieldId": "priority",
            "key": "priority",
            "name": "Priority",
            "required": False,
            "schema": {"type": "priority"},
            "allowedValues": priority_catalog(),
        },
        {
            "fieldId": "assignee",
            "key": "assignee",
            "name": "Assignee",
            "required": False,
            "schema": {"type": "user"},
        },
        {
            "fieldId": "labels",
            "key": "labels",
            "name": "Labels",
            "required": False,
            "schema": {"type": "array", "items": "string"},
        },
    ]


@router.get("/priority")
async def list_priorities(
    current_user: UserModel = Depends(authenticate_jira),
) -> List[Dict[str, Any]]:
    return priority_catalog()


@router.get("/field")
async def list_fields(
    current_user: UserModel = Depends(authenticate_jira),
) -> List[Dict[str, Any]]:
    # 无自定义字段（sprint/storyPoints 发现落空即安全，探测 §3）
    return []


@router.get("/filter/favourite")
async def list_favourite_filters(
    current_user: UserModel = Depends(authenticate_jira),
) -> List[Dict[str, Any]]:
    return []


# ============================================================================
# issue 读写（注意：createmeta 路由已在前，/issue/{key} 不会被遮蔽）
# ============================================================================


@router.get("/issue/{key}")
async def get_issue(
    key: str,
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    _ensure_allowed("get")
    issue = await _resolve_issue(service, key)
    return await _issue_payload(service.db, issue)


@router.post("/issue", status_code=201)
async def create_issue(
    payload: Dict[str, Any] = Body(...),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    _ensure_allowed("create")
    fields = payload.get("fields") or {}
    summary = (fields.get("summary") or "").strip()
    if not summary:
        raise jira_bad_request("summary 不能为空", field="summary")

    issue_type = _resolve_issue_type(fields.get("issuetype"))
    priority = _resolve_priority(fields.get("priority"))

    assignee_id: Optional[str] = None
    assignee_ref = fields.get("assignee")
    if isinstance(assignee_ref, dict):
        ref = assignee_ref.get("accountId") or assignee_ref.get("name")
        user = await _resolve_user_ref(service.db, ref)
        if user is None and ref:
            raise jira_bad_request(f"assignee 用户不存在: {ref}", field="assignee")
        assignee_id = str(user.id) if user else None

    description = fields.get("description")
    if description is not None and not isinstance(description, str):
        raise jira_bad_request("description 必须是字符串（server 模式纯文本）", field="description")

    issue = await service.create_issue(
        IssueCreate(
            title=summary,
            description=description,
            type=issue_type,
            status="open",
            priority=priority,
            assignee_id=assignee_id,
        ),
        str(current_user.id),
        dept_id=None,
    )

    labels = fields.get("labels")
    if isinstance(labels, list) and labels:
        await sync_issue_labels(service, issue.id, [str(x) for x in labels], str(current_user.id))

    return {
        "id": issue.id,
        "key": issue_code_to_key(issue.issue_code),
        "self": f"/rest/api/2/issue/{issue.id}",
    }


def _resolve_issue_type(raw: Any) -> str:
    """issuetype {id}|{name}|裸串 → IssueType token；未命中 400"""
    token: Optional[str] = None
    if isinstance(raw, dict):
        token = raw.get("id") or raw.get("name")
    elif isinstance(raw, str):
        token = raw
    if not token:
        return IssueType.FEATURE.value
    lowered = str(token).strip().lower()
    for t in IssueType:
        if lowered == t.value.lower() or lowered == display_name(t.value).lower():
            return t.value
    raise jira_bad_request(f"issue type 不存在: {token}", field="issuetype")


def _resolve_priority(raw: Any) -> str:
    if raw is None:
        return IssuePriority.MEDIUM.value
    token: Optional[str] = None
    if isinstance(raw, dict):
        token = raw.get("id") or raw.get("name")
    elif isinstance(raw, str):
        token = raw
    if not token:
        return IssuePriority.MEDIUM.value
    lowered = str(token).strip().lower()
    for p in IssuePriority:
        if lowered == p.value.lower() or lowered == display_name(p.value).lower():
            return p.value
    raise jira_bad_request(f"priority 不存在: {token}", field="priority")


@router.put("/issue/{key}", status_code=204)
async def update_issue(
    key: str,
    payload: Dict[str, Any] = Body(...),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Response:
    _ensure_allowed("update")
    issue = await _resolve_issue(service, key)
    fields: Dict[str, Any] = payload.get("fields") or {}
    update_ops: Dict[str, Any] = payload.get("update") or {}

    issue_fields: Dict[str, Any] = {}
    if "summary" in fields:
        summary = (fields.get("summary") or "").strip()
        if not summary:
            raise jira_bad_request("summary 不能为空", field="summary")
        issue_fields["title"] = summary
    if "description" in fields:
        if fields["description"] is not None and not isinstance(fields["description"], str):
            raise jira_bad_request("description 必须是字符串", field="description")
        issue_fields["description"] = fields["description"]
    if "priority" in fields:
        raw = fields["priority"]
        if raw is None:
            issue_fields["priority"] = None
        elif isinstance(raw, dict) and not (raw.get("id") or raw.get("name")):
            issue_fields["priority"] = None
        else:
            issue_fields["priority"] = _resolve_priority(raw)
    if "issuetype" in fields:
        issue_fields["type"] = _resolve_issue_type(fields["issuetype"])

    if issue_fields:
        await service.update_issue(issue.id, IssueUpdate(**issue_fields), str(current_user.id))

    # labels：fields.labels 整体替换 / update.labels 增删（Orca 两选一，LBt）
    if isinstance(fields.get("labels"), list):
        await sync_issue_labels(
            service, issue.id, [str(x) for x in fields["labels"]], str(current_user.id)
        )
    label_ops = update_ops.get("labels")
    if isinstance(label_ops, list) and label_ops:
        current_names = set(await _current_label_names(service, issue.id))
        for op in label_ops:
            if not isinstance(op, dict):
                continue
            if "add" in op:
                current_names.add(str(op["add"]))
            if "remove" in op:
                current_names.discard(str(op["remove"]))
        await sync_issue_labels(service, issue.id, sorted(current_names), str(current_user.id))

    return Response(status_code=204)


async def _current_label_names(service: IssueService, issue_id: str) -> List[str]:
    """当前标签名列表（update.labels 增删基线）"""
    from opentask.api.tasks.service import get_issue_current_tags

    current = await get_issue_current_tags(service.db, issue_id)
    return list(current)


@router.put("/issue/{key}/assignee", status_code=204)
async def assign_issue(
    key: str,
    payload: Dict[str, Any] = Body(...),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Response:
    _ensure_allowed("update")
    issue = await _resolve_issue(service, key)
    ref = None
    if isinstance(payload, dict):
        ref = payload.get("name")
        if ref is None:
            ref = payload.get("accountId")
    if ref is None:
        await service.update_issue(issue.id, IssueUpdate(assignee_id=None), str(current_user.id))
        return Response(status_code=204)
    user = await _resolve_user_ref(service.db, ref)
    if user is None:
        raise jira_bad_request(f"assignee 用户不存在: {ref}", field="assignee")
    await service.update_issue(issue.id, IssueUpdate(assignee_id=str(user.id)), str(current_user.id))
    return Response(status_code=204)


# ============================================================================
# transitions（状态流转，探测 §3）
# ============================================================================


@router.get("/issue/{key}/transitions")
async def list_transitions(
    key: str,
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    _ensure_allowed("get")
    issue = await _resolve_issue(service, key)
    current_generic = issue_status_to_generic(issue.status)
    return {"expand": "transitions", "transitions": available_transitions(current_generic)}


@router.post("/issue/{key}/transitions", status_code=204)
async def transition_issue(
    key: str,
    payload: Dict[str, Any] = Body(...),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Response:
    _ensure_allowed("transition")
    issue = await _resolve_issue(service, key)
    transition = payload.get("transition") or {}
    target = transition.get("id") if isinstance(transition, dict) else None
    if not target:
        raise jira_bad_request("transition.id 不能为空", field="transition")

    vocabulary = get_generic_statuses()
    target = str(target).strip().lower()
    matched = next((t for t in vocabulary if t.lower() == target), None)
    if matched is None:
        raise jira_status_unknown(
            f"transition 目标状态 {target!r} 不在生效词表内", field="transition"
        )
    if matched == issue_status_to_generic(issue.status):
        raise jira_bad_request(
            f"issue 已处于状态 {matched}，无此流转", field="transition"
        )

    await service.update_issue(
        issue.id, IssueUpdate(status=generic_status_to_issue(matched)), str(current_user.id)
    )

    # update.comment add（LBt 的 transitionComment；多条逐条落库）
    update_ops = payload.get("update") or {}
    comments = update_ops.get("comment") if isinstance(update_ops, dict) else None
    if isinstance(comments, list):
        for op in comments:
            if isinstance(op, dict) and isinstance(op.get("add"), dict):
                body = (op["add"].get("body") or "").strip()
                if body:
                    await service.add_comment(issue.id, body, str(current_user.id))

    return Response(status_code=204)


# ============================================================================
# comments（Orca BB 翻页读法：startAt/maxResults/total，探测 §3）
# ============================================================================


async def _comment_payloads(
    db: AsyncSession, comments: List[IssueComment]
) -> List[Dict[str, Any]]:
    user_ids = {c.user_id for c in comments if c.user_id}
    users: Dict[str, UserModel] = {}
    if user_ids:
        result = await db.execute(select(UserModel).where(UserModel.id.in_(list(user_ids))))
        users = {str(u.id): u for u in result.scalars().all()}
    return [
        {
            "id": c.id,
            "self": f"/rest/api/2/issue/{c.issue_id}/comment/{c.id}",
            "body": c.content or "",
            "author": user_object(users.get(c.user_id)),
            "updateAuthor": user_object(users.get(c.user_id)),
            "created": jira_timestamp(c.created_at),
            "updated": jira_timestamp(c.updated_at),
        }
        for c in comments
    ]


@router.get("/issue/{key}/comment")
async def list_comments(
    key: str,
    startAt: int = Query(0, ge=0),
    maxResults: int = Query(50, ge=1, le=100),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    _ensure_allowed("get")
    issue = await _resolve_issue(service, key)

    from sqlalchemy import func

    base = select(IssueComment).where(
        IssueComment.issue_id == issue.id,
        IssueComment.is_deleted == False,  # noqa: E712
    )
    total = (
        await service.db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0
    result = await service.db.execute(
        base.order_by(IssueComment.created_at.asc(), IssueComment.id.asc())
        .offset(startAt)
        .limit(maxResults)
    )
    comments = list(result.scalars().all())
    return {
        "startAt": startAt,
        "maxResults": maxResults,
        "total": total,
        "comments": await _comment_payloads(service.db, comments),
    }


@router.post("/issue/{key}/comment", status_code=201)
async def add_comment(
    key: str,
    payload: Dict[str, Any] = Body(...),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> Dict[str, Any]:
    _ensure_allowed("update")
    issue = await _resolve_issue(service, key)
    body = payload.get("body")
    if not isinstance(body, str) or not body.strip():
        raise jira_bad_request("comment body 不能为空", field="body")
    comment = await service.add_comment(issue.id, body, str(current_user.id))
    payload = await _comment_payloads(service.db, [comment])
    return payload[0]


# ============================================================================
# 用户查找（assignee list / user search，探测 §3：server 参数名 username）
# ============================================================================


async def _search_users(
    db: AsyncSession, query: Optional[str], max_results: int
) -> List[Dict[str, Any]]:
    """用户名/展示名包含匹配（ci）；'.'（Orca server 空查询哨兵）视为不过滤"""
    stmt = select(UserModel).order_by(UserModel.username.asc())
    if query and query.strip() and query.strip() != ".":
        kw = f"%{query.strip()}%"
        stmt = stmt.where(
            UserModel.username.ilike(kw) | UserModel.name.ilike(kw)
        )
    result = await db.execute(stmt.limit(max_results))
    return [user_object(u) for u in result.scalars().all()]  # type: ignore[misc]


@router.get("/user/assignable/search")
async def assignable_users(
    key: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    maxResults: int = Query(50, ge=1, le=100),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> List[Dict[str, Any]]:
    return await _search_users(service.db, username or query, maxResults)


@router.get("/user/search")
async def search_users(
    username: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    maxResults: int = Query(50, ge=1, le=100),
    service: ContractIssueService = Depends(get_jira_service),
    current_user: UserModel = Depends(authenticate_jira),
) -> List[Dict[str, Any]]:
    return await _search_users(service.db, username or query, maxResults)
