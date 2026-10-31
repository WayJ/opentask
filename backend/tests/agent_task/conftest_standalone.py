"""
Agent Task Service 独立测试配置

不依赖数据库迁移，直接测试服务层逻辑
"""

import pytest


@pytest.fixture
def task_service():
    """创建新的 TaskService 实例用于测试"""
    from opentask.services.agent_task.service import TaskService
    return TaskService()


# 清理单例，确保测试之间隔离
@pytest.fixture(autouse=True)
def reset_task_service_singleton():
    """每个测试后重置任务服务单例"""
    yield
    from opentask.services.agent_task.service import _task_service
    global _task_service
    _task_service = None
