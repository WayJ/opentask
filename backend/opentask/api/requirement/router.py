"""需求模块 API 路由"""
import logging
import json
import os
from typing import Any, AsyncIterator, Optional
import mimetypes
from io import BytesIO
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from opentask.models.requirement.schema import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
    RequirementWithEvents,
    RequirementListResponse,
    RequirementStatistics,
    TimelineResponse,
    AssignRequest,
)
from opentask.models.requirement.enums import RequirementStatus, Priority, EventType
from opentask.models.requirement.model import Requirement, Comment
from opentask.models.document.model import Document
from opentask.models.user.model import UserModel
from opentask.auth import authenticate
from opentask.models.document.schema import DocumentUpdate, DocumentResponse
from opentask.models.document.enums import DocumentStatus
from opentask.models.task.schema import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskImportData,
    TaskImportResponse,
)
from opentask.models.task.enums import TaskStatus, TaskType
from opentask.services.requirement.service import RequirementService
from opentask.services.requirement.task_service import TaskService
from opentask.services.user_center.rbac_service import RbacService
from opentask.services.storage.service import get_storage_service
from opentask.repositories.base import get_session
from opentask.utils.response import success_response, error_response, StatusCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/requirements", tags=["Requirements"], deprecated=True)


async def get_requirement_service(
    db: AsyncSession = Depends(get_session)
) -> RequirementService:
    """获取需求服务依赖"""
    return RequirementService(db)


async def get_task_service(
    db: AsyncSession = Depends(get_session)
) -> TaskService:
    """获取任务服务依赖"""
    return TaskService(db)


# ============================================================================
# 任务管理接口（需求任务分解）
# ============================================================================


@router.get("/{requirement_id}/tasks")
async def list_requirement_tasks(
    requirement_id: str,
    status: Optional[TaskStatus] = None,
    assigned_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: TaskService = Depends(get_task_service),
    current_user: UserModel = Depends(authenticate),
):
    """
    获取需求下的任务列表

    返回树形结构（最多两级：父任务 -> 子任务），包含每个任务的关联文档。
    数据范围过滤：按 tasks 表自身 dept_id 过滤（与父需求可见性独立，本期简化处理）。
    """
    # 数据范围：ALL → None（零过滤）；SELF → 空集（结果恒空）
    visible_dept_ids = await RbacService(service.db).get_visible_dept_ids(current_user)

    tasks = await service.get_by_requirement(
        requirement_id=requirement_id,
        status=status,
        assigned_to=assigned_to,
        visible_dept_ids=visible_dept_ids,
    )

    # 批量加载所有任务的文档
    task_ids = [task.id for task in tasks]
    documents_map: dict[str, list] = {task_id: [] for task_id in task_ids}

    if task_ids:
        doc_query = select(Document).where(
            Document.entity_type == "task",
            Document.entity_id.in_(task_ids)
        )
        doc_result = await service.db.execute(doc_query)
        documents = doc_result.scalars().all()

        for doc in documents:
            if doc.entity_id not in documents_map:
                documents_map[doc.entity_id] = []
            documents_map[doc.entity_id].append({
                "id": doc.id,
                "file_name": doc.file_name,
                "status": doc.status.value,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
            })

    # 构建树形结构
    task_map: dict[str, dict] = {}
    root_tasks: list[dict] = []

    # 先建立映射并添加根任务
    for task in tasks:
        task_dict = service.to_response(task, children=[], documents=documents_map.get(task.id, []))
        task_map[task.id] = task_dict
        if not task.parent_id:
            root_tasks.append(task_dict)

    # 添加子任务到父任务
    for task in tasks:
        if task.parent_id and task.parent_id in task_map:
            parent_dict = task_map[task.parent_id]
            parent_dict["children"].append(service.to_response(task, children=[], documents=documents_map.get(task.id, [])))

    # 按排序
    def sort_by_order(tasks_list):
        tasks_list.sort(key=lambda t: t.get("order", 0))

    sort_by_order(root_tasks)
    for task_dict in task_map.values():
        if task_dict["children"]:
            sort_by_order(task_dict["children"])

    # 分页 - 只对根任务分页
    total = len(root_tasks)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_tasks = root_tasks[start:end]

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    return success_response(data={
        "rows": paginated_tasks,
        "total": total,
        "current": page,
        "pageSize": page_size,
        "totalPages": total_pages
    })


@router.post("/{requirement_id}/tasks")
async def create_requirement_task(
    requirement_id: str,
    dto: TaskCreate,
    service: TaskService = Depends(get_task_service),
    current_user: UserModel = Depends(authenticate),
):
    """
    为需求创建任务

    - **title**: 任务标题（必填）
    - **description**: 任务描述
    - **task_type**: 任务类型 (design/implement/test/review/deploy/document/research)
    - **assigned_to**: 分配给谁
    - **input_data**: 任务输入参数
    - **depends_on**: 依赖的任务 ID 列表
    """
    try:
        # 部门归属快照：取创建人主部门
        dept_id = await RbacService(service.db).get_primary_dept_id(current_user)
        # 确保 requirement_id 一致
        dto.requirement_id = requirement_id
        task = await service.create(dto, dept_id=dept_id)
        return success_response(data=service.to_response(task), message="任务创建成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{requirement_id}/tasks/{task_id}")
async def get_requirement_task(
    requirement_id: str,
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    """获取任务详情"""
    try:
        task = await service.get_by_id(task_id)

        # 获取依赖和被依赖的任务
        dependencies = await service.get_dependencies(task_id)
        dependents = await service.get_dependents(task_id)

        response_data = service.to_response(task)
        response_data["dependencies"] = [d.id for d in dependencies]
        response_data["dependents"] = [d.id for d in dependents]

        return success_response(data=response_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{requirement_id}/tasks/{task_id}")
async def update_requirement_task(
    requirement_id: str,
    task_id: str,
    dto: TaskUpdate,
    service: TaskService = Depends(get_task_service),
):
    """
    更新任务

    支持更新标题、描述、状态、优先级、分配人、输出、产物等
    """
    try:
        task = await service.update(task_id, dto)
        return success_response(data=service.to_response(task), message="任务更新成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{requirement_id}/tasks/{task_id}")
async def delete_requirement_task(
    requirement_id: str,
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    """删除任务"""
    try:
        await service.delete(task_id)
        return success_response(message="任务删除成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{requirement_id}/tasks/{task_id}/start")
async def start_requirement_task(
    requirement_id: str,
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    """
    开始执行任务

    检查依赖是否完成,如果完成则将状态更新为 RUNNING
    """
    try:
        can_start, blocking = await service.can_start(task_id)

        if not can_start:
            return error_response(
                message="任务依赖未完成",
                data={"blocking_tasks": blocking}
            )

        task = await service.update(task_id, TaskUpdate(status=TaskStatus.RUNNING))
        return success_response(data=service.to_response(task), message="任务已开始")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{requirement_id}/tasks/{task_id}/complete")
async def complete_requirement_task(
    requirement_id: str,
    task_id: str,
    output_data: dict = None,
    artifacts: dict = None,
    service: TaskService = Depends(get_task_service),
):
    """
    完成任务

    标记任务为 COMPLETED 状态,记录输出和产物
    """
    try:
        task = await service.update(task_id, TaskUpdate(
            status=TaskStatus.COMPLETED,
            output_data=output_data,
            artifacts=artifacts
        ))
        return success_response(data=service.to_response(task), message="任务已完成")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{requirement_id}/tasks/{task_id}/fail")
async def fail_requirement_task(
    requirement_id: str,
    task_id: str,
    error_message: str,
    service: TaskService = Depends(get_task_service),
):
    """
    标记任务失败

    记录错误信息,增加重试计数
    """
    try:
        task = await service.update(task_id, TaskUpdate(
            status=TaskStatus.FAILED,
            error_message=error_message
        ))
        return success_response(data=service.to_response(task), message="任务已标记为失败")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{requirement_id}/tasks/import")
async def import_requirement_tasks(
    requirement_id: str,
    file: UploadFile = File(..., description="task.json 文件"),
    service: TaskService = Depends(get_task_service),
):
    """
    批量导入任务

    上传 task.json 文件，批量创建任务。支持的标准格式：
    ```json
    {
      "project": "项目名称",
      "description": "项目描述",
      "tasks": [
        {
          "id": 1,
          "title": "任务标题",
          "description": "任务描述",
          "steps": ["步骤1", "步骤2"],
          "controller": "Controller名称",
          "path": "文件路径",
          "status": "completed",
          "passes": true
        }
      ]
    }
    ```
    """
    try:
        # 读取并解析 JSON 文件
        content = await file.read()
        try:
            import_data = TaskImportData(**json.loads(content.decode("utf-8")))
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"无效的 JSON 文件: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"解析任务数据失败: {str(e)}")

        # 映射原始 ID 到新创建的任务 ID
        id_mapping: dict[int, str] = {}
        created_tasks: list[TaskResponse] = []
        errors: list[str] = []
        imported_count = 0
        failed_count = 0

        # 第一遍：创建所有任务（不处理依赖）
        for item in import_data.tasks:
            try:
                # 映射状态
                task_status = TaskStatus.PENDING
                if item.status:
                    status_lower = item.status.lower()
                    if status_lower in ("completed", "done", "finished"):
                        task_status = TaskStatus.COMPLETED
                    elif status_lower in ("in_progress", "running", "active"):
                        task_status = TaskStatus.RUNNING
                    elif status_lower in ("failed", "error"):
                        task_status = TaskStatus.FAILED

                # 构建输入数据
                input_data = {}
                if item.controller:
                    input_data["controller"] = item.controller
                if item.path:
                    input_data["path"] = item.path
                if item.steps:
                    input_data["steps"] = item.steps

                # 合并描述和步骤
                description = item.description or ""
                if item.steps:
                    if description:
                        description += "\n\n步骤：\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(item.steps))
                    else:
                        description = "步骤：\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(item.steps))

                # 创建任务
                task_create = TaskCreate(
                    requirement_id=requirement_id,
                    title=item.title,
                    description=description[:2000] if description else None,
                    task_type=item.task_type,
                    input_data=input_data if input_data else None,
                    depends_on=None
                )

                task = await service.create(task_create)
                created_tasks.append(service.to_response(task))

                # 保存 ID 映射
                if item.id is not None:
                    id_mapping[item.id] = task.id

                imported_count += 1
                logger.info(f"导入任务: {task.title} ({task.id})")

            except Exception as e:
                failed_count += 1
                error_msg = f"任务 '{item.title}' 导入失败: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        # 第二遍：处理依赖关系
        for item in import_data.tasks:
            if item.depends_on and item.id is not None:
                try:
                    task_id = id_mapping.get(item.id)
                    if not task_id:
                        continue

                    # 转换依赖 ID
                    new_depends_on = []
                    for dep_id in item.depends_on:
                        if dep_id in id_mapping:
                            new_depends_on.append(id_mapping[dep_id])

                    if new_depends_on:
                        await service.update_dependencies(task_id, new_depends_on)
                        logger.info(f"更新任务 {task_id} 的依赖: {new_depends_on}")

                except Exception as e:
                    error_msg = f"任务 '{item.title}' 依赖处理失败: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        return success_response(data={
            "requirement_id": requirement_id,
            "imported_count": imported_count,
            "failed_count": failed_count,
            "tasks": created_tasks,
            "errors": errors
        }, message=f"成功导入 {imported_count} 个任务" + (f"，{failed_count} 个失败" if failed_count > 0 else ""))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("导入任务时发生错误")
        raise HTTPException(status_code=500, detail=f"导入任务失败: {str(e)}")


@router.post("/{requirement_id}/tasks/regenerate-codes")
async def regenerate_requirement_task_codes(
    requirement_id: str,
    service: TaskService = Depends(get_task_service),
):
    """
    批量重新生成需求下所有任务的编码

    重新计算并更新所有任务的编码字段，确保编码正确反映任务的层级关系
    """
    try:
        code_map = await service.regenerate_task_codes(requirement_id)
        return success_response(data=code_map, message=f"成功重新生成 {len(code_map)} 个任务的编码")
    except Exception as e:
        logger.exception("重新生成任务编码时发生错误")
        raise HTTPException(status_code=500, detail=f"重新生成任务编码失败: {str(e)}")


# ============================================================================
# 任务文档管理接口
# ============================================================================


@router.get("/{requirement_id}/tasks/{task_id}/documents")
async def get_task_documents(
    requirement_id: str,
    task_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    """获取任务的文档列表"""
    try:
        from sqlalchemy import func

        count_query = select(func.count()).select_from(
            select(Document)
            .where(
                Document.entity_type == "task",
                Document.entity_id == task_id
            ).subquery()
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        query = select(Document).where(
            Document.entity_type == "task",
            Document.entity_id == task_id
        ).order_by(Document.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        documents = result.scalars().all()

        return success_response(data={
            "data": [DocumentResponse.model_validate(d) for d in documents],
            "total": total,
            "page": page,
            "page_size": page_size
        })
    except Exception as e:
        logger.error(f"Error getting task documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{requirement_id}/tasks/{task_id}/documents", status_code=status.HTTP_201_CREATED)
async def create_task_document(
    requirement_id: str,
    task_id: str,
    file: UploadFile = File(..., description="上传的文件"),
    doc_status: DocumentStatus = Form(DocumentStatus.DRAFT, description="文档状态"),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(authenticate),
):
    """为任务创建文档（上传文件）"""
    try:
        storage_path, filename, file_size = await get_storage_service().save_upload_file(
            file,
            subdir=f"tasks/{task_id}"
        )

        mime_type = mimetypes.guess_type(filename)[0] or file.content_type or 'application/octet-stream'

        # 部门归属快照：取上传人主部门
        dept_id = await RbacService(db).get_primary_dept_id(current_user)

        doc = Document(
            entity_type="task",
            entity_id=task_id,
            file_path=storage_path,
            file_name=filename,
            file_type=mime_type,
            file_size=file_size,
            status=doc_status,
            dept_id=dept_id,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        logger.info(f"Created document {doc.id} for task {task_id}")
        return success_response(
            data=DocumentResponse.model_validate(doc),
            message="文档创建成功"
        )
    except Exception as e:
        logger.error(f"Error creating task document: {e}")
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{requirement_id}/tasks/{task_id}/documents/{document_id}")
async def delete_task_document(
    requirement_id: str,
    task_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_session),
):
    """删除任务的文档"""
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.entity_type == "task",
                Document.entity_id == task_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        get_storage_service().delete_file(doc.file_path)
        await db.delete(doc)
        await db.commit()

        logger.info(f"Deleted document {document_id} from task {task_id}")
        return success_response(message="文档删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task document: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_requirement(
    dto: RequirementCreate,
    service: RequirementService = Depends(get_requirement_service),
    current_user: UserModel = Depends(authenticate),
):
    """
    创建需求

    - **title**: 需求标题（必填）
    - **description**: 需求描述
    - **priority**: 优先级（low/medium/high/critical）
    - **tags**: 标签列表
    - **created_by**: 创建者 ID
    """
    # 部门归属快照：取创建人主部门写入（无归属则保持 NULL）
    dept_id = await RbacService(service.db).get_primary_dept_id(current_user)
    # 创建者以认证身份为准（前端遗留 payload 硬编码 'admin'，不信任客户端字段）。
    # 存 user.id：列表 SELF 兜底按 created_by == user_id 匹配，回填也优先 UUID。
    dto.created_by = str(current_user.id)
    requirement = await service.create(dto, dept_id=dept_id)
    return success_response(data=service.to_response(requirement), message="需求创建成功")


@router.get("")
async def list_requirements(
    status: RequirementStatus | None = None,
    priority: Priority | None = None,
    assignee_id: str | None = None,
    project_id: str | None = Query(None, description="按项目 ID 筛选需求"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: RequirementService = Depends(get_requirement_service),
    current_user: UserModel = Depends(authenticate),
):
    """
    获取需求列表

    支持按状态、优先级、负责人、项目过滤和分页。
    数据范围过滤：按部门可见集 + "或本人创建"过滤（ALL 档零过滤）。
    """
    # 数据范围：ALL → None（零过滤）；SELF → 空集 + creator 条件（只见本人）
    visible_dept_ids = await RbacService(service.db).get_visible_dept_ids(current_user)

    result = await service.get_list(
        status, priority, assignee_id, project_id, page, page_size,
        visible_dept_ids=visible_dept_ids,
        user_id=str(current_user.id),
    )
    return success_response(data=result)


@router.get("/search")
async def search_requirements(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    service: RequirementService = Depends(get_requirement_service),
):
    """
    搜索需求

    按标题和描述搜索
    """
    # service.search 已返回 RequirementResponse 列表（含 project_name），
    # 不能再过 to_response（其读取 ORM 的 .project 关系，对已转换对象会 AttributeError）
    results = await service.search(q, limit)
    return success_response(data=results)


@router.get("/by-code/{code}")
async def get_requirement_by_code(
    code: str,
    service: RequirementService = Depends(get_requirement_service),
):
    """
    通过需求编号获取需求

    - **code**: 需求编号（如 "需求2026-73"）

    用于支持 ?code=需求2026-xx 格式的链接
    """
    requirement = await service.get_by_code(code)
    documents = await service.get_requirement_documents(requirement.id)
    return success_response(data=service.to_response(requirement, documents))


@router.get("/statistics")
async def get_statistics(
    service: RequirementService = Depends(get_requirement_service),
):
    """
    获取需求统计信息

    返回总数、按状态统计、按优先级统计
    """
    stats = await service.get_statistics()
    return success_response(data=stats)


@router.get("/{requirement_id}")
async def get_requirement(
    requirement_id: str,
    service: RequirementService = Depends(get_requirement_service),
):
    """
    获取单个需求

    返回需求基本信息和关联文档
    """
    requirement = await service.get_by_id(requirement_id)
    documents = await service.get_requirement_documents(requirement_id)
    return success_response(data=service.to_response(requirement, documents))


@router.get("/{requirement_id}/timeline")
async def get_requirement_timeline(
    requirement_id: str,
    service: RequirementService = Depends(get_requirement_service),
):
    """
    获取需求时间线

    返回需求的所有事件和各状态耗时
    """
    timeline = await service.get_timeline(requirement_id)
    return success_response(data=timeline)


# @router.get("/{requirement_id}/with-events")
# async def get_requirement_with_events(
#     requirement_id: str,
#     service: RequirementService = Depends(get_requirement_service),
# ):
#     """
#     获取需求详情（包含事件）

#     返回需求基本信息和所有事件
#     """
#     result = await service.get_with_events(requirement_id)
#     return success_response(data=result)


@router.put("/{requirement_id}")
async def update_requirement(
    requirement_id: str,
    dto: RequirementUpdate,
    actor: str | None = Query(None, description="操作者 ID"),
    service: RequirementService = Depends(get_requirement_service),
):
    """
    更新需求

    - **title**: 需求标题
    - **description**: 需求描述
    - **status**: 状态
    - **priority**: 优先级
    - **tags**: 标签列表
    - **assignee_id**: 负责人 ID
    """
    requirement = await service.update(requirement_id, dto, actor)
    return success_response(data=service.to_response(requirement), message="需求更新成功")


@router.post("/{requirement_id}/assign")
async def assign_requirement(
    requirement_id: str,
    dto: AssignRequest,
    actor: str | None = Query(None, description="操作者 ID"),
    service: RequirementService = Depends(get_requirement_service),
):
    """
    分配需求给用户

    - **assignee_id**: 被分配人 ID
    """
    requirement = await service.assign(requirement_id, dto, actor)
    return success_response(data=service.to_response(requirement), message="需求分配成功")


@router.delete("/{requirement_id}")
async def delete_requirement(
    requirement_id: str,
    service: RequirementService = Depends(get_requirement_service),
):
    """
    删除需求

    级联删除所有关联的事件、评论等
    """
    await service.delete(requirement_id)
    return success_response(message="需求删除成功")

# ============================================================================
# 需求文档管理接口（Document = Attachment 简化模型）
# ============================================================================


@router.get("/{requirement_id}/documents")
async def get_requirement_documents(
    requirement_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(authenticate),
):
    """
    获取需求的文档列表

    返回需求关联的所有文档（文档就是附件）。
    数据范围过滤：按部门可见集 + "或本人创建"过滤（ALL 档零过滤）。
    """
    try:
        # TODO: 迁移到 service 层（违反 api 层无数据库操作规范）
        from sqlalchemy import func

        # 数据范围：ALL → None（零过滤）；SELF → 空集 + creator 条件（只见本人）
        rbac = RbacService(db)
        visible_dept_ids = await rbac.get_visible_dept_ids(current_user)

        # 获取文档总数（先注入数据范围过滤再 count）
        base_query = rbac.apply_data_scope(
            select(Document).where(
                Document.entity_type == "requirement",
                Document.entity_id == requirement_id
            ),
            visible_dept_ids,
            dept_col=Document.dept_id,
            creator_col=Document.created_by,
            user_id=str(current_user.id),
        )
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 分页获取文档
        query = base_query.order_by(Document.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        documents = result.scalars().all()

        return success_response(data={
            "data": [DocumentResponse.model_validate(d) for d in documents],
            "total": total,
            "page": page,
            "page_size": page_size
        })
    except Exception as e:
        logger.error(f"Error getting requirement documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{requirement_id}/documents", status_code=status.HTTP_201_CREATED)
async def create_requirement_document(
    requirement_id: str,
    file: UploadFile = File(..., description="上传的文件"),
    doc_status: DocumentStatus = Form(DocumentStatus.DRAFT, description="文档状态"),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(authenticate),
):
    """
    为需求创建文档（上传文件）

    - **file**: 上传的文件（必填，支持图片、PDF、Word 等）
    - **doc_status**: 文档状态（默认 DRAFT）

    文档就是附件，直接上传文件创建文档

    **覆盖逻辑**: 如果同一需求下已存在相同文件名的文档，将删除旧文档并创建新文档
    """
    # 获取原始文件名（用于检查重复）
    original_filename = file.filename
    new_file_path = None

    try:
        # 保存文件到本地存储
        storage_path, filename, file_size = await get_storage_service().save_upload_file(
            file,
            subdir=f"requirements/{requirement_id}"
        )
        new_file_path = storage_path

        # 获取 MIME 类型
        mime_type = mimetypes.guess_type(filename)[0] or file.content_type or 'application/octet-stream'

        # 检查同一需求下是否存在相同文件名的文档
        existing_docs = await db.execute(
            select(Document)
            .where(
                Document.entity_type == "requirement",
                Document.entity_id == requirement_id,
                Document.file_name == original_filename
            )
        )
        existing_doc = existing_docs.scalar_one_or_none()

        # 如果存在同名文档，先删除旧的文档记录和物理文件
        if existing_doc:
            logger.info(f"Found existing document with same filename '{original_filename}' in requirement {requirement_id}, deleting old version")
            try:
                # 获取旧文件的物理路径并删除
                old_file_path = existing_doc.file_path
                if old_file_path:
                    # 构建完整的物理文件路径
                    old_full_path = os.path.join("uploads", old_file_path)
                    if os.path.exists(old_full_path):
                        os.remove(old_full_path)
                        logger.info(f"Deleted old physical file: {old_full_path}")

                # 删除数据库记录
                await db.delete(existing_doc)
                await db.commit()
                logger.info(f"Deleted old document record {existing_doc.id}")
            except Exception as e:
                logger.error(f"Error deleting old document: {e}", exc_info=True)
                await db.rollback()
                # 即使删除失败也继续，因为新文件有不同的文件名

        # 部门归属快照：取上传人主部门
        dept_id = await RbacService(db).get_primary_dept_id(current_user)

        # 创建文档记录
        doc = Document(
            entity_type="requirement",
            entity_id=requirement_id,
            file_path=storage_path,
            file_name=original_filename,  # 保存原始文件名
            file_type=mime_type,
            file_size=file_size,
            status=doc_status,
            dept_id=dept_id,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        logger.info(f"Created document {doc.id} for requirement {requirement_id}")
        return success_response(
            data=DocumentResponse.model_validate(doc),
            message="文档上传成功"
        )
    except HTTPException:
        # HTTP 异常直接抛出
        raise
    except IntegrityError as e:
        # 唯一约束冲突（并发情况下可能发生）
        logger.error(f"IntegrityError creating document: {e}", exc_info=True)
        await db.rollback()
        # 清理已上传的新文件
        if new_file_path:
            try:
                new_full_path = os.path.join("uploads", new_file_path)
                if os.path.exists(new_full_path):
                    os.remove(new_full_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up file after IntegrityError: {cleanup_error}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同名文件正在被其他用户上传，请稍后重试"
        )
    except Exception as e:
        logger.error(f"Error creating requirement document: {e}", exc_info=True)
        await db.rollback()
        # 清理已上传的新文件
        if new_file_path:
            try:
                new_full_path = os.path.join("uploads", new_file_path)
                if os.path.exists(new_full_path):
                    os.remove(new_full_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up file: {cleanup_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档上传失败，请稍后重试"
        )


@router.get("/{requirement_id}/documents/{document_id}")
async def get_requirement_document(
    requirement_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_session),
):
    """获取需求的特定文档"""
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.entity_type == "requirement",
                Document.entity_id == requirement_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        return success_response(data=DocumentResponse.model_validate(doc))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting requirement document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{requirement_id}/documents/{document_id}")
async def update_requirement_document(
    requirement_id: str,
    document_id: str,
    file: UploadFile | None = File(None, description="新的文件（可选）"),
    doc_status: DocumentStatus | None = Form(None, description="文档状态"),
    db: AsyncSession = Depends(get_session),
):
    """
    更新需求的文档

    - **file**: 新的文件（可选，如果提供则替换原有文件）
    - **doc_status**: 文档状态（可选）

    如果提供了新文件，会删除旧文件并上传新文件
    """
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.entity_type == "requirement",
                Document.entity_id == requirement_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 更新字段
        if doc_status is not None:
            doc.status = doc_status

        # 如果提供了新文件，替换旧文件
        if file is not None:
            # 删除旧文件
            get_storage_service().delete_file(doc.file_path)

            # 上传新文件
            storage_path, filename, file_size = await get_storage_service().save_upload_file(
                file,
                subdir=f"requirements/{requirement_id}"
            )

            # 获取 MIME 类型
            mime_type = mimetypes.guess_type(filename)[0] or file.content_type or 'application/octet-stream'

            # 更新文档信息
            doc.file_path = storage_path
            doc.file_name = filename
            doc.file_type = mime_type
            doc.file_size = file_size

        await db.commit()
        await db.refresh(doc)

        logger.info(f"Updated document {document_id} for requirement {requirement_id}")
        return success_response(
            data=DocumentResponse.model_validate(doc),
            message="文档更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating requirement document: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{requirement_id}/documents/{document_id}")
async def delete_requirement_document(
    requirement_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_session),
):
    """
    删除需求的文档

    同时删除数据库记录和存储的文件
    注意：此操作不可撤销
    """
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.entity_type == "requirement",
                Document.entity_id == requirement_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 删除存储的文件
        get_storage_service().delete_file(doc.file_path)

        # 删除数据库记录
        await db.delete(doc)
        await db.commit()

        logger.info(f"Deleted document {document_id} from requirement {requirement_id}")
        return success_response(message="文档删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting requirement document: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{requirement_id}/documents/{document_id}/download")
async def download_requirement_document(
    requirement_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_session),
):
    """
    下载文档文件

    直接返回文件内容，支持浏览器预览或下载
    支持 MinIO 和本地存储两种方式
    """
    try:
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.entity_type == "requirement",
                Document.entity_id == requirement_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 检查文件是否存在
        if not get_storage_service().file_exists(doc.file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 判断存储类型并返回相应的响应
        from opentask.config import config

        # 处理文件名编码：同时提供ASCII fallback和UTF-8编码
        import urllib.parse
        safe_filename = doc.file_name.encode('ascii', 'ignore').decode('ascii') or 'download'
        encoded_filename = urllib.parse.quote(doc.file_name, safe='')
        content_disposition = f"inline; filename=\"{safe_filename}\"; filename*=UTF-8''{encoded_filename}"

        if config.use_minio:
            # MinIO 存储：使用 StreamingResponse 流式传输
            file_stream = get_storage_service().get_file_stream(doc.file_path)

            # 读取文件内容
            content = file_stream.read()
            file_stream.close()

            # 返回流式响应
            # 使用RFC 5987编码支持中文文件名
            return StreamingResponse(
                BytesIO(content),
                media_type=doc.file_type,
                headers={
                    "Content-Disposition": content_disposition
                }
            )
        else:
            # 本地存储：使用 FileResponse
            file_path = get_storage_service().get_file_path(doc.file_path)
            # FileResponse的filename参数会自动处理编码
            return FileResponse(
                path=file_path,
                filename=safe_filename,
                media_type=doc.file_type,
                headers={
                    "Content-Disposition": content_disposition
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 需求评论接口
# ============================================================================


@router.get("/{requirement_id}/comments")
async def get_requirement_comments(
    requirement_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: RequirementService = Depends(get_requirement_service),
):
    """获取需求的所有评论（分页，倒序排列）"""
    try:
        # 使用 service 层获取评论及用户信息
        result = await service.get_comments_with_user_info(requirement_id, page, page_size)

        return success_response(data=result)
    except Exception as e:
        logger.error(f"Error getting comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{requirement_id}/comments")
async def add_requirement_comment(
    requirement_id: str,
    content: str = Form(..., description="评论内容", min_length=1, max_length=500),
    current_user: UserModel = Depends(authenticate),
    db: AsyncSession = Depends(get_session),
):
    """添加需求评论

    限制：
    - content: 1-500 字符
    """
    try:
        # 验证内容长度
        if len(content) > 500:
            raise HTTPException(
                status_code=422,
                detail=f"评论内容过长，最大允许500字符，当前{len(content)}字符"
            )

        # 确保需求存在
        requirement = await db.execute(
            select(Requirement).where(Requirement.id == requirement_id)
        )
        req = requirement.scalar_one_or_none()

        if not req:
            raise HTTPException(status_code=404, detail="需求不存在")

        # 创建评论
        import uuid
        comment = Comment(
            id=str(uuid.uuid4()),
            requirement_id=requirement_id,
            content=content,
            user_id=str(current_user.id),  # 从认证上下文获取用户 ID
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        logger.info(f"Comment added to requirement {requirement_id}")
        return success_response(
            data={
                "id": comment.id,
                "requirement_id": comment.requirement_id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
            },
            message="评论添加成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/comments/{comment_id}")
async def update_requirement_comment(
    comment_id: str,
    content: str = Form(..., description="评论内容"),
    current_user: UserModel = Depends(authenticate),
    db: AsyncSession = Depends(get_session),
):
    """更新需求评论"""
    try:
        # 查询评论
        from opentask.models.requirement.model import Comment

        result = await db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(status_code=404, detail="评论不存在")

        # 检查权限：只有评论作者才能修改
        if comment.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权限修改此评论")

        # 更新内容
        comment.content = content
        comment.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(comment)

        logger.info(f"Comment {comment_id} updated")
        return success_response(
            data={
                "id": comment.id,
                "content": comment.content,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
            },
            message="评论更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating comment: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/comments/{comment_id}")
async def delete_requirement_comment(
    comment_id: str,
    current_user: UserModel = Depends(authenticate),
    db: AsyncSession = Depends(get_session),
):
    """删除需求评论（软删除）"""
    try:
        from opentask.models.requirement.model import Comment

        result = await db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(status_code=404, detail="评论不存在")

        # 检查权限：只有评论作者才能删除
        if comment.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权限删除此评论")

        # 软删除
        comment.is_deleted = True
        comment.updated_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Comment {comment_id} deleted")
        return success_response(message="评论删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
