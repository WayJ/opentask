"""
测试Mission Center API是否能返回从需求创建的任务
"""
import pytest
from sqlalchemy import delete

from opentask.services.requirement.task_service import TaskService
from opentask.services.mission_center.service import get_task_service
from opentask.models.task.schema import TaskCreate
from opentask.models.task.enums import TaskType
from opentask.models.requirement.model import Requirement
from opentask.repositories.mission_center_repository import AgentTaskRepository
from opentask.repositories.base import SessionCreator
import uuid
from datetime import datetime


@pytest.mark.asyncio
async def test_mission_center_list_shows_requirement_tasks(test_session):
    """
    验证：从需求创建的任务应该出现在Mission Center的列表中
    """
    # 1. 先创建一个测试需求
    requirement = Requirement(
        id=str(uuid.uuid4()),
        code=f"TEST-REQ-API-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试API需求",
        description="用于测试Mission Center API",
        status="draft",
        priority="medium",
        tags=[],
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.commit()
    await test_session.refresh(requirement)

    # 2. 创建顶级任务
    task_data = TaskCreate(
        requirement_id=requirement.id,
        parent_id=None,
        title="API测试任务",
        description="这个任务应该出现在Mission Center API中",
        task_type=TaskType.IMPLEMENT,
        assigned_to=None,
        input_data={},
        depends_on=[]
    )

    task_service = TaskService(test_session)
    created_task = await task_service.create(task_data)

    # 验证任务创建成功且有 agent_task_id
    assert created_task.agent_task_id is not None, "agent_task_id 应该被设置"

    # 3. 使用Mission Center Repository查询任务列表
    async with SessionCreator() as mission_session:
        repo = AgentTaskRepository()
        tasks = await repo.list_tasks(
            session=mission_session,
            status=None,
            assignee=None,
            limit=100,
            offset=0
        )

        # 4. 验证新创建的任务在列表中
        task_ids = [t.task_id for t in tasks]
        assert created_task.agent_task_id in task_ids, \
            f"任务 {created_task.agent_task_id} 应该在Mission Center列表中，但实际列表包含: {task_ids[:5]}..."

        # 5. 获取该任务并验证link_data
        mission_task = await repo.get_task(mission_session, created_task.agent_task_id)
        assert mission_task is not None, "Mission Center中应该能找到该任务"
        assert mission_task.link_data is not None, "link_data不应该为空"
        assert f"task:{created_task.id}" in mission_task.link_data, \
            f"link_data应该包含task:{created_task.id}，实际为: {mission_task.link_data}"

        print(f"[PASS] Mission Center API正常工作！任务ID: {created_task.agent_task_id}")

    # 清理
    mission_service = get_task_service()
    await mission_service.delete_task(created_task.agent_task_id)
    await test_session.delete(requirement)
    await test_session.commit()
