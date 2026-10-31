"""
Agent Task Comment API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pydantic import BaseModel

from opentask.repositories.base import get_session
from opentask.repositories.mission_center_comment_repository import AgentTaskCommentRepository
from opentask.models.mission_center import AgentTaskComment
from opentask.schemas.mission_center import ApiResponse


router = APIRouter(prefix="/comments", tags=["Task Comments"])


class CommentCreateRequest(BaseModel):
    """创建评论请求"""
    content: str
    comment_type: str = "comment"
    agent_id: str = None
    user_id: str = None
    parent_id: int = None


@router.get("/{task_id}", response_model=ApiResponse)
async def get_comments(
    task_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session)
):
    """获取任务的所有评论"""
    repo = AgentTaskCommentRepository()

    comments = await repo.get_comments(session, task_id, limit, offset)
    count = await repo.get_comment_count(session, task_id)

    return ApiResponse(
        code=200,
        message="success",
        data={
            "comments": [comment.to_dict() for comment in comments],
            "total": count
        },
        timestamp=int(datetime.utcnow().timestamp() * 1000)
    )


@router.post("/{task_id}", response_model=ApiResponse)
async def create_comment(
    task_id: str,
    request: CommentCreateRequest,
    session: AsyncSession = Depends(get_session)
):
    """添加评论"""
    repo = AgentTaskCommentRepository()

    comment = await repo.create_comment(
        session=session,
        task_id=task_id,
        content=request.content,
        comment_type=request.comment_type,
        agent_id=request.agent_id,
        user_id=request.user_id,
        parent_id=request.parent_id
    )

    await session.commit()

    return ApiResponse(
        code=200,
        message="Comment created successfully",
        data=comment.to_dict(),
        timestamp=int(datetime.utcnow().timestamp() * 1000)
    )


@router.delete("/{comment_id}", response_model=ApiResponse)
async def delete_comment(
    comment_id: int,
    session: AsyncSession = Depends(get_session)
):
    """删除评论"""
    repo = AgentTaskCommentRepository()
    success = await repo.delete_comment(session, comment_id)

    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")

    await session.commit()

    return ApiResponse(
        code=200,
        message="Comment deleted successfully",
        data={"comment_id": comment_id},
        timestamp=int(datetime.utcnow().timestamp() * 1000)
    )
