"""
TDD测试：验证创建任务后能同步到Mission Center

需求2026-123 - 在需求详情页面创建顶级任务时，同步创建到Mission Center

运行方式：
  pytest tests/integration/test_task_sync_to_mission_center.py -v
"""
import pytest
from sqlalchemy import delete

from opentask.services.requirement.task_service import TaskService
from opentask.services.mission_center.service import get_task_service
from opentask.models.task.schema import TaskCreate
from opentask.models.task.enums import TaskType, TaskStatus


@pytest.mark.asyncio
async def test_create_top_level_task_syncs_to_mission_center(test_session):
    """
    RED阶段：创建顶级任务后，应该在Mission Center中能看到

    这个测试应该先失败（因为任务可能没有正确同步），
    然后我们修复代码让它通过。
    """
    import uuid
    from datetime import datetime
    from opentask.models.requirement.model import Requirement

    # 先创建一个测试需求
    requirement = Requirement(
        id=str(uuid.uuid4()),
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求",
        description="用于测试任务同步",
        status="draft",
        priority="medium",
        tags=[],
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.commit()
    await test_session.refresh(requirement)

    # 准备测试数据
    task_data = TaskCreate(
        requirement_id=requirement.id,
        parent_id=None,  # 顶级任务
        title="测试同步任务",
        description="这是一个测试任务，应该同步到Mission Center",
        task_type=TaskType.IMPLEMENT,
        assigned_to=None,
        input_data={},
        depends_on=[]
    )

    # 创建任务（这应该会触发同步到Mission Center）
    task_service = TaskService(test_session)

    # 创建任务
    created_task = await task_service.create(task_data)

    # 验证任务创建成功
    assert created_task is not None
    assert created_task.id is not None
    assert created_task.title == "测试同步任务"

    # 关键验证：agent_task_id 应该被设置
    assert created_task.agent_task_id is not None, \
        f"顶级任务的 agent_task_id 应该被设置，但当前为空"

    # 在Mission Center中查询该任务
    mission_service = get_task_service()
    mission_task = await mission_service.get_task(created_task.agent_task_id)

    # 验证Mission Center中存在该任务
    assert mission_task is not None, \
        f"Mission Center中应该存在任务 {created_task.agent_task_id}"

    # 验证任务的基本信息
    assert mission_task.title == "测试同步任务"
    assert mission_task.description == "这是一个测试任务，应该同步到Mission Center"
    assert mission_task.task_id == created_task.agent_task_id

    # 验证link_data包含正确的关联
    assert mission_task.link_data is not None
    assert f"task:{created_task.id}" in mission_task.link_data

    print(f"[PASS] 测试通过! 任务 {created_task.id} 已同步到 Mission Center: {mission_task.task_id}")

    # 清理：删除Mission Center中的任务和测试需求
    await mission_service.delete_task(mission_task.task_id)
    await test_session.delete(requirement)
    await test_session.commit()


@pytest.mark.asyncio
async def test_create_child_task_does_not_sync_to_mission_center(test_session):
    """
    创建子任务时，不应该同步到Mission Center
    """
    import uuid
    from datetime import datetime
    from opentask.models.requirement.model import Requirement

    # 先创建一个测试需求
    requirement = Requirement(
        id=str(uuid.uuid4()),
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求2",
        description="用于测试子任务不同步",
        status="draft",
        priority="medium",
        tags=[],
        created_by="test_user",
        created_at=datetime.utcnow()
    )
    test_session.add(requirement)
    await test_session.commit()
    await test_session.refresh(requirement)

    # 先创建一个父任务
    parent_data = TaskCreate(
        requirement_id=requirement.id,
        parent_id=None,
        title="父任务",
        description="这是父任务",
        task_type=TaskType.IMPLEMENT,
        assigned_to=None,
        input_data={},
        depends_on=[]
    )

    task_service = TaskService(test_session)
    parent_task = await task_service.create(parent_data)

    # 创建子任务
    child_data = TaskCreate(
        requirement_id=requirement.id,
        parent_id=parent_task.id,  # 子任务
        title="测试子任务",
        description="这是一个子任务，不应该同步到Mission Center",
        task_type=TaskType.IMPLEMENT,
        assigned_to=None,
        input_data={},
        depends_on=[]
    )

    child_task = await task_service.create(child_data)

    # 验证子任务的 agent_task_id 应该为空
    assert child_task.agent_task_id is None, \
        f"子任务的 agent_task_id 应该为空，但当前为 {child_task.agent_task_id}"

    print(f"[PASS] 子任务测试通过! 子任务 {child_task.id} 没有同步到 Mission Center")

    # 清理
    if parent_task.agent_task_id:
        mission_service = get_task_service()
        await mission_service.delete_task(parent_task.agent_task_id)

    await test_session.delete(requirement)
    await test_session.commit()
