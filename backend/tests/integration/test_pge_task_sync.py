"""
测试PGE任务同步到Mission Center

验证创建PGE任务时，父任务能正确同步到Mission Center
"""
import pytest
from sqlalchemy import delete

from opentask.services.task.pge_service import PGETaskService
from opentask.services.mission_center.service import get_task_service
from opentask.models.task.enums import TaskFramework
from opentask.models.requirement.model import Requirement
from opentask.repositories.mission_center_repository import AgentTaskRepository
from opentask.repositories.base import SessionCreator
import uuid
from datetime import datetime


@pytest.mark.asyncio
async def test_pge_task_syncs_to_mission_center(test_session):
    """
    验证：创建PGE任务时，父任务应该同步到Mission Center
    """
    # 1. 先创建一个测试需求
    requirement = Requirement(
        id=str(uuid.uuid4()),
        code=f"TEST-REQ-PGE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试PGE需求",
        description="用于测试PGE任务同步",
        status="draft",
        priority="medium",
        tags=[],
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.commit()
    await test_session.refresh(requirement)

    # 2. 创建PGE任务
    pge_service = PGETaskService(test_session)
    parent_task = await pge_service.create_pge_task(
        requirement_id=requirement.id,
        title="PGE测试任务",
        description="这是一个PGE测试任务",
        framework=TaskFramework.PGE,
        required_skills=[]
    )

    # 3. 验证父任务创建成功
    assert parent_task is not None
    assert parent_task.id is not None
    assert parent_task.framework == TaskFramework.PGE.value

    # 4. 验证agent_task_id被设置
    assert parent_task.agent_task_id is not None, \
        f"PGE父任务的 agent_task_id 应该被设置，但当前为空"

    print(f"[PASS] PGE任务创建成功，agent_task_id: {parent_task.agent_task_id}")

    # 5. 在Mission Center中查询该任务
    async with SessionCreator() as mission_session:
        repo = AgentTaskRepository()
        mission_task = await repo.get_task(mission_session, parent_task.agent_task_id)

        # 验证Mission Center中存在该任务
        assert mission_task is not None, \
            f"Mission Center中应该存在任务 {parent_task.agent_task_id}"

        # 验证任务的基本信息
        assert mission_task.title == "PGE测试任务"
        assert mission_task.task_id == parent_task.agent_task_id

        # 验证link_data包含正确的关联
        assert mission_task.link_data is not None
        assert f"task:{parent_task.id}" in mission_task.link_data, \
            f"link_data应该包含task:{parent_task.id}，实际为: {mission_task.link_data}"

        print(f"[PASS] PGE任务已同步到 Mission Center: {mission_task.task_id}")

    # 清理
    mission_service = get_task_service()
    await mission_service.delete_task(parent_task.agent_task_id)

    # 删除所有子任务
    from opentask.models.task.model import Task
    await test_session.execute(delete(Task).where(Task.parent_id == parent_task.id))
    await test_session.delete(parent_task)
    await test_session.delete(requirement)
    await test_session.commit()

    print("[PASS] 测试完成，数据已清理")
