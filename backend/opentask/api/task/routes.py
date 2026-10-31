"""PGE 任务 API 路由

提供 PGE 任务创建和提示词生成的 RESTful API 接口。
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.models.task.enums import TaskStatus
from opentask.models.task.schema import PGETaskCreate, TaskResponse
from opentask.services.task.pge_service import PGETaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ============================================================================
# 依赖注入
# ============================================================================


async def get_db():
    """获取数据库会话"""
    async for session in get_session():
        yield session


# ============================================================================
# 响应模型
# ============================================================================


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="消息")
    data: dict | None = Field(None, description="数据")
    timestamp: int = Field(..., description="时间戳")


class PGETaskResponse(BaseModel):
    """PGE 任务创建响应"""
    code: int = 200
    message: str = "PGE 任务创建成功"
    data: dict | None = None
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


class TaskPromptResponseData(BaseModel):
    """任务提示词响应数据"""
    task_id: str
    prompt: str


class TaskPromptApiResponse(BaseModel):
    """任务提示词 API 响应"""
    code: int = 200
    message: str = "success"
    data: TaskPromptResponseData | None = None
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


class PGETaskPreviewRequest(BaseModel):
    """PGE 任务提示词预览请求"""
    requirement_title: str = Field(..., description="需求标题")
    requirement_id: str = Field(..., description="需求ID")
    description: str | None = Field(None, description="任务描述")
    required_skills: list[str] = Field(default_factory=list, description="必需技能")


# ============================================================================
# API 接口
# ============================================================================


@router.post("", response_model=PGETaskResponse)
async def create_pge_task(
    request: PGETaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    创建 PGE 任务（含 3 个子任务）

    请求体：
    - requirement_id: 所属需求 ID
    - title: 任务标题
    - description: 任务描述（可选）
    - framework: 任务框架（当前仅支持 PGE）
    - required_skills: 必需的 Superpower Skills（可选）

    响应：
    - code: 状态码
    - message: 消息
    - data: 创建的任务（包含子任务）
    - timestamp: 时间戳
    """
    try:
        # 创建 PGE 任务服务
        service = PGETaskService(db)

        # 创建 PGE 任务
        task = await service.create_pge_task(
            requirement_id=request.requirement_id,
            title=request.title,
            description=request.description,
            framework=request.framework,
            required_skills=request.required_skills,
        )

        # 查询子任务
        from sqlalchemy import select
        from opentask.models.task.model import Task as TaskModel

        stmt = select(TaskModel).where(TaskModel.parent_id == task.id)
        result = await db.execute(stmt)
        subtasks = result.scalars().all()

        # 构造响应数据
        task_data = {
            "id": task.id,
            "requirement_id": task.requirement_id,
            "title": task.title,
            "description": task.description,
            "framework": task.framework,
            "status": task.status,
            "required_skills": task.required_skills,
            "agent_task_id": task.agent_task_id,  # 添加 agent_task_id 字段
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "children": [
                {
                    "id": subtask.id,
                    "code": subtask.code,
                    "title": subtask.title,
                    "description": subtask.description,
                    "task_type": subtask.task_type,
                    "status": subtask.status,
                }
                for subtask in subtasks
            ],
        }

        logger.info(f"PGE 任务创建成功: {task.id}")

        return PGETaskResponse(
            code=200,
            message="PGE 任务创建成功",
            data=task_data,
        )

    except ValueError as e:
        logger.error(f"创建 PGE 任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"创建 PGE 任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建 PGE 任务失败: {str(e)}",
        )


@router.post("/preview-prompt", response_model=TaskPromptApiResponse)
async def preview_pge_task_prompt(
    request_data: PGETaskPreviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    预览 PGE 任务提示词（不需要创建任务）

    请求体：
    - requirement_title: 需求标题
    - requirement_id: 需求ID
    - description: 任务描述（可选）
    - required_skills: 必需技能（可选）

    响应：
    - code: 状态码
    - message: 消息
    - data: 任务提示词
      - task_id: preview（预览标识）
      - prompt: 结构化的任务提示词（Markdown 格式）
    - timestamp: 时间戳
    """
    try:
        from opentask.services.task.prompt_preview_renderer import render_preview_prompt

        # 生成预览提示词
        prompt = await render_preview_prompt(
            requirement_title=request_data.requirement_title,
            requirement_id=request_data.requirement_id,
            description=request_data.description,
            required_skills=request_data.required_skills,
        )

        logger.info(f"预览任务提示词成功: {request_data.requirement_title}")

        return TaskPromptApiResponse(
            code=200,
            message="success",
            data={
                "task_id": "preview",
                "prompt": prompt,
            },
        )

    except Exception as e:
        logger.error(f"预览任务提示词失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览任务提示词失败: {str(e)}",
        )


@router.get("/{task_id}/prompt", response_model=TaskPromptApiResponse)
async def get_task_prompt(
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    获取任务提示词

    路径参数：
    - task_id: 任务 ID（支持完整ID或短ID前8位）

    响应：
    - code: 状态码
    - message: 消息
    - data: 任务提示词
      - task_id: 任务 ID
      - prompt: 结构化的任务提示词（Markdown 格式）
    - timestamp: 时间戳
    """
    try:
        # 创建 PGE 任务服务
        service = PGETaskService(db)

        # 解析任务ID（支持短ID）
        resolved_task_id = await service.resolve_task_id(task_id)

        # 生成任务提示词
        prompt = await service.generate_task_prompt(resolved_task_id)

        logger.info(f"获取任务提示词成功: {task_id} -> {resolved_task_id}")

        return TaskPromptApiResponse(
            code=200,
            message="success",
            data={
                "task_id": resolved_task_id,  # 返回解析后的完整ID
                "prompt": prompt,
            },
        )

    except ValueError as e:
        logger.error(f"获取任务提示词失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"获取任务提示词失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务提示词失败: {str(e)}",
        )


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    获取任务详情

    路径参数：
    - task_id: 任务 ID

    响应：
    - 任务详细信息
    """
    try:
        from sqlalchemy import select
        from opentask.models.task.model import Task as TaskModel

        stmt = select(TaskModel).where(TaskModel.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}",
            )

        # 查询子任务
        stmt = select(TaskModel).where(TaskModel.parent_id == task_id)
        result = await db.execute(stmt)
        subtasks = result.scalars().all()

        # 构造响应数据
        task_data = {
            "id": task.id,
            "requirement_id": task.requirement_id,
            "parent_id": task.parent_id,
            "code": task.code,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "framework": task.framework,
            "status": task.status,
            "required_skills": task.required_skills,
            "assigned_to": task.assigned_to,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "input_data": task.input_data,
            "output_data": task.output_data,
            "artifacts": task.artifacts,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "children": [
                {
                    "id": subtask.id,
                    "code": subtask.code,
                    "title": subtask.title,
                    "description": subtask.description,
                    "task_type": subtask.task_type,
                    "status": subtask.status,
                }
                for subtask in subtasks
            ],
        }

        return ApiResponse(
            code=200,
            message="success",
            data=task_data,
            timestamp=int(datetime.now().timestamp() * 1000),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务详情失败: {str(e)}",
        )
