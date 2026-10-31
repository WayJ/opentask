"""PGE Task Service Unit Tests

简化版的单元测试，用于验证核心功能。
"""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.task.enums import TaskFramework, TaskStatus, TaskType
from opentask.services.task.pge_service import PGETaskService
from datetime import datetime


@pytest.mark.asyncio
async def test_create_pge_task(test_session: AsyncSession):
    """测试创建 PGE 任务"""
    import uuid
    from opentask.models.requirement.model import Requirement
    from datetime import datetime

    # 先创建一个 requirement（外键约束要求）
    requirement_id = str(uuid.uuid4())
    requirement = Requirement(
        id=requirement_id,
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求",
        description="这是一个测试需求，用于测试 PGE 任务创建",
        status="draft",
        priority="medium",
        tags=[],
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.flush()

    # 创建 PGE 任务
    service = PGETaskService(test_session)
    task = await service.create_pge_task(
        requirement_id=requirement_id,  # 使用真实的 requirement ID
        title="测试任务",
        description="这是一个测试任务",
        framework=TaskFramework.PGE,
        required_skills=[
            "superpowers:brainstorming",
            "superpowers:test-driven-development"
        ]
    )

    # 验证父任务
    assert task.id is not None
    assert task.title == "测试任务"
    assert task.framework == "PGE"
    assert task.status == TaskStatus.PENDING.value
    assert task.required_skills is not None
    assert "superpowers:brainstorming" in task.required_skills["skills"]

    # 验证子任务数量（需要在事务中查询）
    # 这里简化测试，实际应该查询数据库验证子任务


@pytest.mark.asyncio
async def test_create_pge_task_invalid_skills(test_session: AsyncSession):
    """测试创建 PGE 任务 - 无效的技能"""
    service = PGETaskService(test_session)

    # 应该抛出 ValueError
    with pytest.raises(ValueError, match="无效的 Superpower Skills"):
        await service.create_pge_task(
            requirement_id="test-req-123",
            title="测试任务",
            description="这是一个测试任务",
            framework=TaskFramework.PGE,
            required_skills=["invalid:skill"]
        )


@pytest.mark.asyncio
async def test_calculate_parent_status_all_pending(test_session: AsyncSession):
    """测试父任务状态计算 - 全部 PENDING"""
    import uuid
    from sqlalchemy import select
    from opentask.models.requirement.model import Requirement
    from opentask.models.task.model import Task
    from datetime import datetime

    # 先创建一个 requirement
    requirement_id = str(uuid.uuid4())
    requirement = Requirement(
        tags=[],
        id=requirement_id,
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求",
        description="测试父任务状态计算",
        status="draft",
        priority="medium",
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.flush()

    # 创建父任务和子任务
    service = PGETaskService(test_session)
    parent_task = await service.create_pge_task(
        requirement_id=requirement_id,
        title="父任务测试",
        description="测试父任务状态计算",
        framework=TaskFramework.PGE,
        required_skills=[]
    )

    # 验证子任务都是 PENDING
    stmt = select(Task).where(Task.parent_id == parent_task.id)
    result = await test_session.execute(stmt)
    subtasks = result.scalars().all()

    assert len(subtasks) == 3
    for subtask in subtasks:
        assert subtask.status == TaskStatus.PENDING.value

    # 计算父任务状态
    parent_status = await service.calculate_parent_status(parent_task.id)
    assert parent_status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_generate_task_prompt(test_session: AsyncSession):
    """测试生成任务提示词"""
    import uuid
    from opentask.models.requirement.model import Requirement
    from datetime import datetime

    # 先创建一个 requirement
    requirement_id = str(uuid.uuid4())
    requirement = Requirement(
        tags=[],
        id=requirement_id,
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求",
        description="测试提示词生成",
        status="draft",
        priority="medium",
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.flush()

    # 创建 PGE 任务
    service = PGETaskService(test_session)
    task = await service.create_pge_task(
        requirement_id=requirement_id,
        title="测试提示词生成",
        description="测试任务提示词生成功能",
        framework=TaskFramework.PGE,
        required_skills=["superpowers:brainstorming"]
    )

    # 生成提示词
    prompt = await service.generate_task_prompt(task.id)

    # 验证提示词内容
    assert isinstance(prompt, str)
    assert "PGE 任务" in prompt
    assert "测试提示词生成" in prompt
    assert "Plan（规划）" in prompt
    assert "Generation（生成）" in prompt
    assert "Evaluation（评估）" in prompt
    assert "brainstorming" in prompt


@pytest.mark.asyncio
async def test_generate_task_prompt_task_not_found(test_session: AsyncSession):
    """测试生成任务提示词 - 任务不存在"""
    service = PGETaskService(test_session)

    # 应该抛出 ValueError
    with pytest.raises(ValueError, match="任务不存在"):
        await service.generate_task_prompt("non-existent-task-id")


@pytest.mark.asyncio
async def test_calculate_parent_status_all_done(test_session: AsyncSession):
    """测试父任务状态计算 - 全部完成"""
    import uuid
    from sqlalchemy import select, update
    from opentask.models.requirement.model import Requirement
    from opentask.models.task.model import Task
    from datetime import datetime

    # 先创建一个 requirement
    requirement_id = str(uuid.uuid4())
    requirement = Requirement(
        tags=[],
        id=requirement_id,
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求",
        description="测试父任务状态计算",
        status="draft",
        priority="medium",
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.flush()

    # 创建父任务和子任务
    service = PGETaskService(test_session)
    parent_task = await service.create_pge_task(
        requirement_id=requirement_id,
        title="父任务测试",
        description="测试父任务状态计算",
        framework=TaskFramework.PGE,
        required_skills=[]
    )

    # 更新所有子任务为 COMPLETED
    stmt = select(Task).where(Task.parent_id == parent_task.id)
    result = await test_session.execute(stmt)
    subtasks = result.scalars().all()

    for subtask in subtasks:
        subtask.status = TaskStatus.COMPLETED.value

    # 计算父任务状态
    parent_status = await service.calculate_parent_status(parent_task.id)
    assert parent_status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_calculate_parent_status_failed(test_session: AsyncSession):
    """测试父任务状态计算 - 有失败"""
    import uuid
    from sqlalchemy import select
    from opentask.models.requirement.model import Requirement
    from opentask.models.task.model import Task
    from datetime import datetime

    # 先创建一个 requirement
    requirement_id = str(uuid.uuid4())
    requirement = Requirement(
        tags=[],
        id=requirement_id,
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求",
        description="测试父任务状态计算",
        status="draft",
        priority="medium",
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.flush()

    # 创建父任务和子任务
    service = PGETaskService(test_session)
    parent_task = await service.create_pge_task(
        requirement_id=requirement_id,
        title="父任务测试",
        description="测试父任务状态计算",
        framework=TaskFramework.PGE,
        required_skills=[]
    )

    # 更新第一个子任务为 FAILED
    stmt = select(Task).where(Task.parent_id == parent_task.id)
    result = await test_session.execute(stmt)
    subtasks = result.scalars().all()

    subtasks[0].status = TaskStatus.FAILED.value
    subtasks[1].status = TaskStatus.COMPLETED.value
    subtasks[2].status = TaskStatus.COMPLETED.value

    # 计算父任务状态
    parent_status = await service.calculate_parent_status(parent_task.id)
    assert parent_status == TaskStatus.FAILED


# ============================================================================
# 集成测试
# ============================================================================


@pytest.mark.asyncio
async def test_create_pge_task_api(test_session: AsyncSession, admin_token: str):
    """测试创建 PGE 任务 API 集成"""
    from httpx import AsyncClient, ASGITransport
    from opentask.app import App
    from opentask.models.requirement.model import Requirement

    # 创建测试需求
    requirement_id = str(uuid.uuid4())
    requirement = Requirement(
        id=requirement_id,
        code=f"TEST-REQ-API-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="API 测试需求",
        description="用于 API 集成测试的需求",
        status="draft",
        priority="medium",
        tags=[],
        created_by="admin",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.commit()

    # 创建 FastAPI 测试客户端
    app = App()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"}
    ) as client:
        # 测试创建 PGE 任务
        response = await client.post(
            "/api/tasks",
            json={
                "requirement_id": requirement_id,
                "title": "API 测试任务",
                "description": "通过 API 创建的 PGE 任务",
                "framework": "PGE",
                "required_skills": ["superpowers:brainstorming"]
            }
        )

        # 验证响应（简化验证，只检查关键字段）
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "PGE 任务创建成功"
        assert data["data"]["title"] == "API 测试任务"
        assert data["data"]["framework"] == "PGE"
        assert "children" in data["data"]
        assert len(data["data"]["children"]) == 3  # 应该有 3 个子任务
