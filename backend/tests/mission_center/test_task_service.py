"""
测试 TaskService 新方法
"""
import pytest
from datetime import datetime
from opentask.services.mission_center.service import TaskService, TaskStatus


@pytest.mark.asyncio
async def test_get_source_context_requirement(test_session, test_requirement):
    """测试获取需求上下文"""
    service = TaskService()

    context = await service.get_source_context("requirement", str(test_requirement.id))

    assert context["source_type"] == "requirement"
    assert context["source_id"] == str(test_requirement.id)
    assert context["source_code"] == test_requirement.code
    assert context["source_title"] == test_requirement.title


@pytest.mark.asyncio
async def test_get_source_context_issue(test_session):
    """测试获取 Issue 上下文"""
    from opentask.models.issue.model import Issue
    import uuid

    service = TaskService()

    # 创建测试 Issue
    issue = Issue(
        id=str(uuid.uuid4()),
        issue_code=f"TEST-ISSUE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}",
        title="测试 Issue",
        description="这是一个测试 Issue",
        type="bug",
        status="open",
        priority="medium",
        reporter_id="test_user",
        created_at=datetime.utcnow()
    )

    test_session.add(issue)
    await test_session.commit()
    await test_session.refresh(issue)

    try:
        context = await service.get_source_context("issue", str(issue.id))

        assert context["source_type"] == "issue"
        assert context["source_id"] == str(issue.id)
        assert context["source_code"] == issue.issue_code
        assert context["source_title"] == issue.title
    finally:
        await test_session.delete(issue)
        await test_session.commit()


@pytest.mark.asyncio
async def test_get_source_context_not_found(test_session):
    """测试获取不存在的源对象"""
    service = TaskService()

    with pytest.raises(ValueError, match="源对象不存在"):
        await service.get_source_context("requirement", "non-existent-id")


def test_build_task_description():
    """测试构建任务描述"""
    service = TaskService()

    context = {
        "source_type": "requirement",
        "source_code": "REQ-001",
        "source_title": "测试需求"
    }

    description = service.build_task_description(
        context,
        "/task-create 优化性能",
        "优化性能"
    )

    assert "REQ-001" in description
    assert "优化性能" in description
    assert "需求" in description
    assert "/task-create" in description
    assert "斜杠命令创建" in description


@pytest.mark.asyncio
async def test_create_task_with_links(test_session):
    """测试创建带关联的任务"""
    service = TaskService()

    task = await service.create_task_with_links(
        title="测试任务",
        description="测试描述",
        link_data=["requirement:test-uuid", "issue:test-uuid"],
        context={"source_type": "requirement", "source_code": "REQ-001"},
        created_by="user123",
        priority="high"
    )

    assert task.title == "测试任务"
    assert task.link_data == ["requirement:test-uuid", "issue:test-uuid"]
    assert task.status == TaskStatus.PENDING
    assert task.priority.value == "high"
    assert len(task.logs) > 0
    assert task.logs[0]["type"] == "info"
    assert "user123" in task.logs[0]["message"]


@pytest.mark.asyncio
async def test_create_task_with_assignee(test_session):
    """测试创建带分配人的任务"""
    service = TaskService()

    task = await service.create_task_with_links(
        title="测试任务",
        description="测试描述",
        link_data=["requirement:test-uuid"],
        context={},
        created_by="user123",
        assignee="agent-001"
    )

    assert task.assignee == "agent-001"
    assert task.status == TaskStatus.PENDING
