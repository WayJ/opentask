"""工作管理服务层测试"""
import pytest
from datetime import date, datetime
from opentask.services.work_management_service import WorkManagementService


@pytest.mark.asyncio
async def test_create_rd_group(test_session, test_director_id, test_leader_id):
    """测试创建研发组"""
    service = WorkManagementService(test_session)
    group = await service.create_rd_group(
        name="测试组",
        director_id=test_director_id,
        leader_id=test_leader_id
    )

    # create_rd_group 按服务契约返回 dict（避免 relationship 序列化问题）
    assert group["id"] is not None
    assert group["name"] == "测试组"
    assert group["director_id"] == test_director_id
    assert group["leader_id"] == test_leader_id


@pytest.mark.asyncio
async def test_create_cost_project(test_session, test_manager_id):
    """测试创建成本项目"""
    from opentask.schemas.work_management.cost_project_schema import CostProjectCreate

    service = WorkManagementService(test_session)
    project_data = CostProjectCreate(
        name="测试项目",
        code="TEST-SVC-001",
        description="服务层测试项目",
        manager_id=test_manager_id
    )
    project = await service.create_cost_project(project_data)

    assert project.id is not None
    assert project.name == "测试项目"
    assert project.code == "TEST-SVC-001"


@pytest.mark.asyncio
async def test_create_work_assignment(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试创建工作安排"""
    from opentask.schemas.work_management.work_assignment_schema import WorkAssignmentCreate

    service = WorkManagementService(test_session)
    assignment_data = WorkAssignmentCreate(
        title="服务层测试工作",
        assignee_id=test_assignee_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 30),
        estimated_hours=5.0,
        week_start=date(2026, 4, 21)
    )
    assignment = await service.create_work_assignment(assignment_data, test_director_id)

    assert assignment.id is not None
    assert assignment.title == "服务层测试工作"
    assert assignment.assigner_id == test_director_id


@pytest.mark.asyncio
async def test_check_overdue_assignment(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试延期检测"""
    from opentask.models.work_management.work_assignment_model import WorkAssignment

    # 创建一个已过期的工作
    past_date = date(2026, 4, 1)
    assignment = WorkAssignment(
        title="过期测试工作",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=past_date,  # 已过期
        estimated_hours=8.0,
        week_start=date(2026, 3, 31),
        status="not_started"
    )
    test_session.add(assignment)
    await test_session.commit()

    service = WorkManagementService(test_session)
    is_overdue, days = service.check_overdue(assignment)

    assert is_overdue is True
    assert days > 0


@pytest.mark.asyncio
async def test_add_group_member(test_session, test_rd_group_id, test_member_id):
    """测试添加组成员"""
    service = WorkManagementService(test_session)
    member = await service.add_group_member(
        group_id=test_rd_group_id,
        user_id=test_member_id,
        role="member"
    )

    assert member.id is not None
    assert member.group_id == test_rd_group_id
    assert member.user_id == test_member_id
    assert member.role == "member"


@pytest.mark.asyncio
async def test_create_work_feedback(test_session, test_assignee_id):
    """测试创建工作反馈"""
    from opentask.schemas.work_management.work_feedback_schema import WorkFeedbackCreate

    service = WorkManagementService(test_session)
    feedback_data = WorkFeedbackCreate(
        assignment_id=None,
        feedback_date=date(2026, 4, 18),
        content="服务层测试反馈",
        status="in_progress",
        is_planned=True
    )
    feedback = await service.create_work_feedback(feedback_data, test_assignee_id)

    assert feedback.id is not None
    assert feedback.content == "服务层测试反馈"
    assert feedback.user_id == test_assignee_id
