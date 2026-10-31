"""工作管理 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional
from datetime import date

from opentask.repositories.base import get_session
from opentask.services.work_management_service import WorkManagementService
from opentask.schemas.work_management import (
    RdGroupCreate, RdGroupUpdate, RdGroupResponse,
    CostProjectCreate, CostProjectUpdate, CostProjectResponse,
    WorkAssignmentCreate, WorkAssignmentUpdate, WorkAssignmentResponse,
    WorkFeedbackCreate, WorkFeedbackUpdate, WorkFeedbackResponse
)

router = APIRouter(prefix="/api/work-management", tags=["work-management"])

async def get_db():
    """获取数据库会话"""
    async for session in get_session():
        yield session


# ============ 研发组管理 ============

@router.post("/rd-groups")
async def create_rd_group(
    group_data: RdGroupCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """创建研发组"""
    service = WorkManagementService(db)
    group = await service.create_rd_group(
        name=group_data.name,
        director_id=group_data.director_id,
        leader_id=group_data.leader_id
    )
    return {"code": 200, "data": group, "message": "创建成功"}


@router.get("/rd-groups")
async def get_rd_groups(
    db: Annotated[AsyncSession, Depends(get_db)],
    director_id: Optional[str] = None
):
    """获取研发组列表"""
    service = WorkManagementService(db)
    groups = await service.get_rd_groups(director_id=director_id)
    return {"code": 200, "data": groups, "message": "success"}


@router.get("/rd-groups/{group_id}")
async def get_rd_group(
    group_id: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取研发组详情"""
    service = WorkManagementService(db)
    group = await service.get_rd_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="研发组不存在")
    return {"code": 200, "data": group, "message": "success"}


@router.post("/rd-groups/{group_id}/members")
async def add_group_member(
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: str,
    user_id: str,
    role: str = "member"
):
    """添加组成员"""
    service = WorkManagementService(db)
    member = await service.add_group_member(group_id, user_id, role)
    return {"code": 200, "data": member, "message": "添加成功"}


@router.delete("/rd-groups/{group_id}/members/{user_id}")
async def remove_group_member(
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: str,
    user_id: str
):
    """移除组成员"""
    service = WorkManagementService(db)
    success = await service.remove_group_member(group_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="成员不存在")
    return {"code": 200, "data": None, "message": "删除成功"}


# ============ 成本项目管理 ============

@router.post("/cost-projects")
async def create_cost_project(
    project_data: CostProjectCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """创建成本项目"""
    service = WorkManagementService(db)
    project = await service.create_cost_project(project_data)
    return {"code": 200, "data": project, "message": "创建成功"}


@router.get("/cost-projects")
async def get_cost_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    manager_id: Optional[str] = None
):
    """获取成本项目列表"""
    service = WorkManagementService(db)
    projects = await service.get_cost_projects(manager_id=manager_id)
    return {"code": 200, "data": projects, "message": "success"}


@router.get("/cost-projects/{project_id}")
async def get_cost_project(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str
):
    """获取成本项目详情（含统计）"""
    service = WorkManagementService(db)
    result = await service.get_cost_project_with_stats(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="成本项目不存在")
    return {"code": 200, "data": result, "message": "success"}


# ============ 工作安排 ============

@router.post("/work-assignments")
async def create_work_assignment(
    assignment_data: WorkAssignmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    assigner_id: str = Query(..., description="分配人ID")  # 从 JWT token 获取
):
    """创建工作安排"""
    service = WorkManagementService(db)
    assignment = await service.create_work_assignment(assignment_data, assigner_id)
    return {"code": 200, "data": assignment, "message": "创建成功"}


@router.get("/work-assignments")
async def get_work_assignments(
    db: Annotated[AsyncSession, Depends(get_db)],
    assignee_id: Optional[str] = None,
    group_id: Optional[str] = None,
    week_start: Optional[date] = None
):
    """获取工作安排列表"""
    service = WorkManagementService(db)
    assignments = await service.get_work_assignments(assignee_id, group_id, week_start)

    # 检查延期状态
    result = []
    for assignment in assignments:
        data = {
            "id": assignment.id,
            "title": assignment.title,
            "assignee_id": assignment.assignee_id,
            "assigner_id": assignment.assigner_id,
            "group_id": assignment.group_id,
            "cost_project_id": assignment.cost_project_id,
            "deadline": assignment.deadline.isoformat() if assignment.deadline else None,
            "estimated_hours": float(assignment.estimated_hours) if assignment.estimated_hours else 0,
            "week_start": assignment.week_start.isoformat() if assignment.week_start else None,
            "status": assignment.status,
            "quality": assignment.quality,
            "related_type": assignment.related_type,
            "related_id": assignment.related_id,
            "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
            "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None,
        }
        is_overdue, days = service.check_overdue(assignment)
        data["is_overdue"] = is_overdue
        data["overdue_days"] = days
        result.append(data)

    return {"code": 200, "data": result, "message": "success"}


@router.get("/work-assignments/{assignment_id}")
async def get_work_assignment(
    db: Annotated[AsyncSession, Depends(get_db)],
    assignment_id: str
):
    """获取工作安排详情"""
    from opentask.models.work_management import WorkAssignment

    service = WorkManagementService(db)
    assignment = await db.get(WorkAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="工作安排不存在")

    is_overdue, days = service.check_overdue(assignment)
    data = {
        "id": assignment.id,
        "title": assignment.title,
        "assignee_id": assignment.assignee_id,
        "assigner_id": assignment.assigner_id,
        "group_id": assignment.group_id,
        "cost_project_id": assignment.cost_project_id,
        "deadline": assignment.deadline.isoformat() if assignment.deadline else None,
        "estimated_hours": float(assignment.estimated_hours) if assignment.estimated_hours else 0,
        "week_start": assignment.week_start.isoformat() if assignment.week_start else None,
        "status": assignment.status,
        "quality": assignment.quality,
        "related_type": assignment.related_type,
        "related_id": assignment.related_id,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
        "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None,
        "is_overdue": is_overdue,
        "overdue_days": days
    }

    return {"code": 200, "data": data, "message": "success"}


# ============ 工作反馈 ============

@router.post("/work-feedback")
async def create_work_feedback(
    feedback_data: WorkFeedbackCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = Query(..., description="用户ID")  # 从 JWT token 获取
):
    """提交工作反馈"""
    service = WorkManagementService(db)
    feedback = await service.create_work_feedback(feedback_data, user_id)
    return {"code": 200, "data": feedback, "message": "提交成功"}


@router.get("/work-feedback")
async def get_work_feedback(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = Query(..., description="用户ID")  # 从 JWT token 获取
):
    """获取我的反馈历史"""
    # 实现获取反馈列表逻辑
    return {"code": 200, "data": [], "message": "success"}


# ============ 我的周视图 ============

@router.get("/my-weekly-work")
async def get_my_weekly_work(
    db: Annotated[AsyncSession, Depends(get_db)],
    week_start: date = Query(..., description="周开始日期（周一）"),
    user_id: str = Query(..., description="用户ID")  # 从 JWT token 获取
):
    """获取我的周工作（计划+遗留）"""
    service = WorkManagementService(db)

    # 获取本周工作
    current_week = await service.get_work_assignments(
        assignee_id=user_id,
        week_start=week_start
    )

    # 获取所有工作用于筛选遗留
    all_assignments = await service.get_work_assignments(assignee_id=user_id)
    overdue = [a for a in all_assignments if a.week_start < week_start and a.status != "completed"]

    # 统计
    total_estimated = sum(float(a.estimated_hours) for a in current_week)
    completed_count = sum(1 for a in current_week if a.status == "completed")

    return {
        "code": 200,
        "data": {
            "current_week": current_week,
            "overdue": overdue,
            "summary": {
                "total_estimated_hours": total_estimated,
                "completed_count": completed_count,
                "pending_count": len(current_week) - completed_count,
                "overdue_count": len(overdue)
            }
        },
        "message": "success"
    }


@router.get("/my-weekly-work/unplanned")
async def get_my_unplanned_work(
    db: Annotated[AsyncSession, Depends(get_db)],
    week_start: date = Query(..., description="周开始日期"),
    user_id: str = Query(..., description="用户ID")  # 从 JWT token 获取
):
    """获取我的计划外工作"""
    service = WorkManagementService(db)
    unplanned = await service.get_unplanned_work(user_id, week_start)
    return {"code": 200, "data": unplanned, "message": "success"}
