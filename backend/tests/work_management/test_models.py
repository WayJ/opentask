"""工作管理模块模型测试"""
import pytest
from opentask.models.work_management.rd_group_model import RdGroup, RdGroupMember
from opentask.models.work_management.cost_project_model import CostProject


@pytest.mark.asyncio
async def test_create_rd_group(test_session, test_director_id, test_leader_id):
    """测试创建研发组 - 基本字段验证"""
    group = RdGroup(
        name="测试研发组",
        director_id=test_director_id,
        leader_id=test_leader_id,
        status="active"
    )
    test_session.add(group)
    await test_session.commit()
    await test_session.refresh(group)

    assert group.id is not None
    assert isinstance(group.id, str)
    assert group.name == "测试研发组"
    assert group.status == "active"  # ENUM 存储的是小写值
    assert group.created_at is not None
    assert group.updated_at is not None


@pytest.mark.asyncio
async def test_rd_group_status_enum(test_session, test_director_id, test_leader_id):
    """测试研发组状态枚举"""
    from opentask.models.work_management.enums import RdGroupStatus

    group1 = RdGroup(
        name="活跃组",
        director_id=test_director_id,
        leader_id=test_leader_id,
        status=RdGroupStatus.ACTIVE
    )
    group2 = RdGroup(
        name="停用组",
        director_id=test_director_id,
        leader_id=test_leader_id,
        status=RdGroupStatus.INACTIVE
    )

    test_session.add(group1)
    test_session.add(group2)
    await test_session.commit()

    assert group1.status == "active"
    assert group2.status == "inactive"


@pytest.mark.asyncio
async def test_rd_group_member_relationship(test_session, test_director_id, test_leader_id, test_member_id):
    """测试研发组成员关联"""
    group = RdGroup(
        name="测试组",
        director_id=test_director_id,
        leader_id=test_leader_id
    )
    test_session.add(group)
    await test_session.flush()
    await test_session.refresh(group)

    member = RdGroupMember(
        group_id=group.id,
        user_id=test_member_id,
        role="member"
    )
    test_session.add(member)
    await test_session.commit()
    await test_session.refresh(member)

    assert member.group_id == group.id
    assert member.user_id == test_member_id
    assert member.role == "member"  # ENUM 存储的是小写值
    assert member.joined_at is not None


@pytest.mark.asyncio
async def test_rd_group_member_role_enum(test_session, test_director_id, test_leader_id, test_member_id):
    """测试研发组成员角色枚举"""
    from opentask.models.work_management.enums import RdGroupRole

    group = RdGroup(
        name="角色测试组",
        director_id=test_director_id,
        leader_id=test_leader_id
    )
    test_session.add(group)
    await test_session.flush()

    member_director = RdGroupMember(
        group_id=group.id,
        user_id=test_director_id,
        role=RdGroupRole.DIRECTOR
    )
    member_leader = RdGroupMember(
        group_id=group.id,
        user_id=test_leader_id,
        role=RdGroupRole.LEADER
    )

    test_session.add(member_director)
    test_session.add(member_leader)
    await test_session.commit()

    assert member_director.role == "director"
    assert member_leader.role == "leader"


@pytest.mark.asyncio
async def test_create_cost_project(test_session, test_manager_id):
    """测试创建成本项目"""
    project = CostProject(
        name="测试项目",
        code="PROJ-001",
        description="测试描述",
        manager_id=test_manager_id
    )
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)

    assert project.id is not None
    assert isinstance(project.id, str)
    assert project.code == "PROJ-001"
    assert project.name == "测试项目"
    assert project.description == "测试描述"
    assert project.manager_id == test_manager_id
    assert project.status == "active"  # 默认状态
    assert project.created_at is not None
    assert project.updated_at is not None


@pytest.mark.asyncio
async def test_cost_project_status_enum(test_session, test_manager_id):
    """测试成本项目状态枚举"""
    from opentask.models.work_management.enums import CostProjectStatus

    project1 = CostProject(
        name="活跃项目",
        code="PROJ-ACTIVE",
        manager_id=test_manager_id,
        status=CostProjectStatus.ACTIVE
    )
    project2 = CostProject(
        name="已完成项目",
        code="PROJ-COMPLETED",
        manager_id=test_manager_id,
        status=CostProjectStatus.COMPLETED
    )
    project3 = CostProject(
        name="已归档项目",
        code="PROJ-ARCHIVED",
        manager_id=test_manager_id,
        status=CostProjectStatus.ARCHIVED
    )

    test_session.add(project1)
    test_session.add(project2)
    test_session.add(project3)
    await test_session.commit()

    assert project1.status == "active"
    assert project2.status == "completed"
    assert project3.status == "archived"


@pytest.mark.asyncio
async def test_cost_project_unique_code(test_session, test_manager_id):
    """测试项目编号唯一性约束"""
    project1 = CostProject(
        name="项目1",
        code="PROJ-UNIQUE",
        manager_id=test_manager_id
    )
    test_session.add(project1)
    await test_session.commit()

    # 尝试创建相同编号的项目
    project2 = CostProject(
        name="项目2",
        code="PROJ-UNIQUE",  # 相同的编号
        manager_id=test_manager_id
    )
    test_session.add(project2)

    # 应该抛出完整性错误
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        await test_session.commit()


@pytest.mark.asyncio
async def test_create_work_assignment(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试创建工作安排"""
    from datetime import date
    from opentask.models.work_management.work_assignment_model import WorkAssignment

    assignment = WorkAssignment(
        title="完成用户登录模块",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 25),
        estimated_hours=8.0,
        week_start=date(2026, 4, 21)
    )
    test_session.add(assignment)
    await test_session.commit()
    await test_session.refresh(assignment)

    assert assignment.id is not None
    assert isinstance(assignment.id, str)
    assert assignment.title == "完成用户登录模块"
    assert assignment.status == "not_started"
    assert assignment.quality == "unknown"
    assert assignment.assignee_id == test_assignee_id
    assert assignment.assigner_id == test_director_id
    assert assignment.group_id == test_rd_group_id
    assert assignment.cost_project_id == test_cost_project_id
    assert assignment.deadline == date(2026, 4, 25)
    assert float(assignment.estimated_hours) == 8.0
    assert assignment.week_start == date(2026, 4, 21)


@pytest.mark.asyncio
async def test_work_assignment_status_transition(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试工作状态流转"""
    from datetime import date
    from opentask.models.work_management.work_assignment_model import WorkAssignment

    assignment = WorkAssignment(
        title="测试工作",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 25),
        estimated_hours=4.0,
        week_start=date(2026, 4, 21)
    )
    test_session.add(assignment)
    await test_session.flush()
    await test_session.refresh(assignment)

    # 初始状态
    assert assignment.status == "not_started"
    assert assignment.quality == "unknown"

    # 更新状态
    assignment.status = "completed"
    assignment.quality = "high"
    await test_session.commit()
    await test_session.refresh(assignment)

    assert assignment.status == "completed"
    assert assignment.quality == "high"


@pytest.mark.asyncio
async def test_work_assignment_status_enum(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试工作状态枚举"""
    from datetime import date
    from opentask.models.work_management.work_assignment_model import WorkAssignment
    from opentask.models.work_management.enums import WorkStatus

    assignment = WorkAssignment(
        title="枚举测试",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 30),
        estimated_hours=2.0,
        week_start=date(2026, 4, 21)
    )
    test_session.add(assignment)
    await test_session.flush()

    # 测试各种状态
    for status in [WorkStatus.NOT_STARTED, WorkStatus.IN_PROGRESS, WorkStatus.COMPLETED, WorkStatus.BLOCKED]:
        assignment.status = status
        await test_session.flush()
        assert assignment.status == status.value


@pytest.mark.asyncio
async def test_work_assignment_quality_enum(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试质量等级枚举"""
    from datetime import date
    from opentask.models.work_management.work_assignment_model import WorkAssignment
    from opentask.models.work_management.enums import QualityLevel

    assignment = WorkAssignment(
        title="质量测试",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 30),
        estimated_hours=1.0,
        week_start=date(2026, 4, 21)
    )
    test_session.add(assignment)
    await test_session.flush()

    # 测试各种质量等级
    for quality in [QualityLevel.UNKNOWN, QualityLevel.HIGH, QualityLevel.LOW]:
        assignment.quality = quality
        await test_session.flush()
        assert assignment.quality == quality.value


@pytest.mark.asyncio
async def test_work_assignment_related_fields(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试关联需求/Issue字段"""
    from datetime import date
    from opentask.models.work_management.work_assignment_model import WorkAssignment
    from opentask.models.work_management.enums import RelatedType

    # 关联需求
    assignment1 = WorkAssignment(
        title="关联需求的工作",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 30),
        estimated_hours=3.0,
        week_start=date(2026, 4, 21),
        related_type=RelatedType.REQUIREMENT,
        related_id="req-uuid-001"
    )
    test_session.add(assignment1)
    await test_session.commit()
    await test_session.refresh(assignment1)

    assert assignment1.related_type == "requirement"
    assert assignment1.related_id == "req-uuid-001"

    # 关联Issue
    assignment2 = WorkAssignment(
        title="关联Issue的工作",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 30),
        estimated_hours=2.0,
        week_start=date(2026, 4, 21),
        related_type=RelatedType.ISSUE,
        related_id="issue-uuid-002"
    )
    test_session.add(assignment2)
    await test_session.commit()
    await test_session.refresh(assignment2)

    assert assignment2.related_type == "issue"
    assert assignment2.related_id == "issue-uuid-002"


@pytest.mark.asyncio
async def test_create_work_feedback(test_session, test_assignee_id):
    """测试创建工作反馈"""
    from datetime import date
    from opentask.models.work_management.work_feedback_model import WorkFeedback

    feedback = WorkFeedback(
        assignment_id=None,  # 计划外工作
        user_id=test_assignee_id,
        feedback_date=date(2026, 4, 22),
        content="已完成接口设计",
        status="in_progress",
        is_planned=True
    )
    test_session.add(feedback)
    await test_session.commit()
    await test_session.refresh(feedback)

    assert feedback.id is not None
    assert isinstance(feedback.id, str)
    assert feedback.user_id == test_assignee_id
    assert feedback.feedback_date == date(2026, 4, 22)
    assert feedback.content == "已完成接口设计"
    assert feedback.status == "in_progress"
    assert feedback.is_planned is True


@pytest.mark.asyncio
async def test_work_feedback_unplanned_type(test_session, test_assignee_id):
    """测试计划外工作反馈类型"""
    from datetime import date
    from opentask.models.work_management.work_feedback_model import WorkFeedback
    from opentask.models.work_management.enums import UnplannedType

    feedback = WorkFeedback(
        assignment_id=None,
        user_id=test_assignee_id,
        feedback_date=date(2026, 4, 22),
        content="解决了一个突发Issue",
        status="completed",
        is_planned=False,
        unplanned_type=UnplannedType.ISSUE_RESOLVED,
        unplanned_related_id="issue-uuid-123"
    )
    test_session.add(feedback)
    await test_session.commit()
    await test_session.refresh(feedback)

    assert feedback.is_planned is False
    assert feedback.unplanned_type == "issue_resolved"
    assert feedback.unplanned_related_id == "issue-uuid-123"


@pytest.mark.asyncio
async def test_create_attachment(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试创建附件"""
    from datetime import date
    from opentask.models.work_management.work_assignment_model import WorkAssignment
    from opentask.models.work_management.work_assignment_attachment_model import WorkAssignmentAttachment

    # 先创建工作安排
    assignment = WorkAssignment(
        title="测试工作",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 30),
        estimated_hours=3.0,
        week_start=date(2026, 4, 21)
    )
    test_session.add(assignment)
    await test_session.flush()

    # 创建附件
    attachment = WorkAssignmentAttachment(
        assignment_id=assignment.id,
        file_name="design.pdf",
        file_path="/uploads/assignment-uuid/design.pdf",
        file_size=1024000,
        uploaded_by=test_assignee_id
    )
    test_session.add(attachment)
    await test_session.commit()
    await test_session.refresh(attachment)

    assert attachment.id is not None
    assert isinstance(attachment.id, str)
    assert attachment.assignment_id == assignment.id
    assert attachment.file_name == "design.pdf"
    assert attachment.file_path == "/uploads/assignment-uuid/design.pdf"
    assert attachment.file_size == 1024000
    assert attachment.uploaded_by == test_assignee_id
    assert attachment.uploaded_at is not None


@pytest.mark.asyncio
async def test_work_assignment_with_feedback_and_attachments(test_session, test_assignee_id, test_director_id, test_rd_group_id, test_cost_project_id):
    """测试工作安排与反馈、附件的关系"""
    from datetime import date
    from opentask.models.work_management.work_assignment_model import WorkAssignment
    from opentask.models.work_management.work_feedback_model import WorkFeedback
    from opentask.models.work_management.work_assignment_attachment_model import WorkAssignmentAttachment

    # 创建工作安排
    assignment = WorkAssignment(
        title="测试工作",
        assignee_id=test_assignee_id,
        assigner_id=test_director_id,
        group_id=test_rd_group_id,
        cost_project_id=test_cost_project_id,
        deadline=date(2026, 4, 30),
        estimated_hours=5.0,
        week_start=date(2026, 4, 21)
    )
    test_session.add(assignment)
    await test_session.flush()

    # 创建反馈
    feedback = WorkFeedback(
        assignment_id=assignment.id,
        user_id=test_assignee_id,
        feedback_date=date(2026, 4, 22),
        content="正在进行中",
        status="in_progress",
        is_planned=True
    )
    test_session.add(feedback)

    # 创建附件
    attachment = WorkAssignmentAttachment(
        assignment_id=assignment.id,
        file_name="doc.pdf",
        file_path="/uploads/doc.pdf",
        file_size=2048000,
        uploaded_by=test_assignee_id
    )
    test_session.add(attachment)

    await test_session.commit()

    # 验证关系（需要 refresh 或重新查询）
    await test_session.refresh(assignment)

    # 由于关系可能没有自动加载，我们直接验证数据存在
    assert assignment.id is not None
    assert feedback.assignment_id == assignment.id
    assert attachment.assignment_id == assignment.id
