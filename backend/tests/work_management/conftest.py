"""工作管理模块测试配置"""
import pytest_asyncio
import uuid
from sqlalchemy import text
from opentask.models.user.model import UserModel


@pytest_asyncio.fixture
async def test_director_id(test_session):
    """创建测试产品总监用户ID"""
    director_uuid = uuid.uuid4()
    director_id = str(director_uuid)

    # 使用 ORM 模型创建用户
    user = UserModel(
        id=director_uuid,
        jnpf_account=f"test_director_{uuid.uuid4().hex[:8]}",
        jnpf_name="测试总监",
        status=1,
        role="admin"
    )
    test_session.add(user)
    await test_session.commit()

    yield director_id

    # 清理
    await test_session.rollback()  # 回滚事务以确保清理


@pytest_asyncio.fixture
async def test_leader_id(test_session):
    """创建测试组长用户ID"""
    leader_uuid = uuid.uuid4()
    leader_id = str(leader_uuid)

    # 使用 ORM 模型创建用户
    user = UserModel(
        id=leader_uuid,
        jnpf_account=f"test_leader_{uuid.uuid4().hex[:8]}",
        jnpf_name="测试组长",
        status=1,
        role="developer"
    )
    test_session.add(user)
    await test_session.commit()

    yield leader_id

    # 清理
    await test_session.rollback()  # 回滚事务以确保清理


@pytest_asyncio.fixture
async def test_member_id(test_session):
    """创建测试成员用户ID"""
    member_uuid = uuid.uuid4()
    member_id = str(member_uuid)

    # 使用 ORM 模型创建用户
    user = UserModel(
        id=member_uuid,
        jnpf_account=f"test_member_{uuid.uuid4().hex[:8]}",
        jnpf_name="测试成员",
        status=1,
        role="viewer"
    )
    test_session.add(user)
    await test_session.commit()

    yield member_id

    # 清理
    await test_session.rollback()  # 回滚事务以确保清理


@pytest_asyncio.fixture
async def test_rd_group_id(test_session, test_director_id, test_leader_id):
    """创建测试研发组ID"""
    from opentask.models.work_management.rd_group_model import RdGroup

    group = RdGroup(
        name="测试研发组",
        director_id=test_director_id,
        leader_id=test_leader_id,
        status="active"
    )
    test_session.add(group)
    await test_session.commit()
    await test_session.refresh(group)

    yield group.id

    # 清理会在每个测试函数后自动进行（通过test_engine fixture的drop_all）


@pytest_asyncio.fixture
async def test_manager_id(test_session):
    """创建测试项目经理用户ID"""
    manager_uuid = uuid.uuid4()
    manager_id = str(manager_uuid)

    # 使用 ORM 模型创建用户
    user = UserModel(
        id=manager_uuid,
        jnpf_account=f"test_manager_{uuid.uuid4().hex[:8]}",
        jnpf_name="测试经理",
        status=1,
        role="manager"
    )
    test_session.add(user)
    await test_session.commit()

    yield manager_id

    # 清理
    await test_session.rollback()  # 回滚事务以确保清理


@pytest_asyncio.fixture
async def test_cost_project_id(test_session, test_manager_id):
    """创建测试成本项目ID"""
    from opentask.models.work_management.cost_project_model import CostProject

    # 使用唯一的 code 避免重复键错误
    project = CostProject(
        name="测试成本项目",
        code=f"TEST-PROJ-{uuid.uuid4().hex[:8].upper()}",
        description="用于测试的成本项目",
        manager_id=test_manager_id,
        status="active"
    )
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)

    yield project.id

    # 清理会在每个测试函数后自动进行


@pytest_asyncio.fixture
async def test_assignee_id(test_session):
    """创建测试被分配人用户ID（工作安排的接收者）"""
    assignee_uuid = uuid.uuid4()
    assignee_id = str(assignee_uuid)

    # 使用 ORM 模型创建用户
    user = UserModel(
        id=assignee_uuid,
        jnpf_account=f"test_assignee_{uuid.uuid4().hex[:8]}",
        jnpf_name="测试被分配人",
        status=1,
        role="developer"
    )
    test_session.add(user)
    await test_session.commit()

    yield assignee_id

    # 清理
    await test_session.rollback()  # 回滚事务以确保清理
