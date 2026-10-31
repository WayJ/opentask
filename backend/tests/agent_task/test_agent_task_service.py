"""
Agent Task Service 单元测试

测试任务管理服务的核心业务逻辑（不依赖数据库）
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
    _task_service = None


from opentask.services.agent_task.service import (
    TaskService,
    Task,
    TaskPriority,
    TaskStatus,
    get_task_service,
)


class TestTaskCreation:
    """任务创建测试"""

    def test_create_task_success(self, task_service):
        """测试成功创建任务"""
        service = task_service
        task = service.create_task(
            title="测试任务",
            description="这是一个测试任务",
            priority=TaskPriority.HIGH,
            assignee="agent-001",
            deadline="2025-12-31T23:59:59Z",
            metadata={"project": "test-project"},
            requirements=["REQ-001"],
        )

        assert task is not None
        assert task.title == "测试任务"
        assert task.description == "这是一个测试任务"
        assert task.priority == TaskPriority.HIGH
        assert task.assignee == "agent-001"
        assert task.status == TaskStatus.PENDING
        assert task.progress_percentage == 0
        assert task.task_id.startswith("task_")

    def test_create_task_with_minimal_params(self):
        """测试使用最小参数创建任务"""
        service = TaskService()
        task = service.create_task(
            title="最小任务",
            description="只有必填字段",
            priority=TaskPriority.MEDIUM,
            assignee="agent-002",
        )

        assert task is not None
        assert task.title == "最小任务"
        assert task.deadline is None
        assert task.metadata == {}
        assert task.requirements == []

    def test_create_task_generates_unique_id(self):
        """测试每个任务都有唯一 ID"""
        service = TaskService()
        task1 = service.create_task(
            title="任务1",
            description="描述1",
            priority=TaskPriority.LOW,
            assignee="agent-001",
        )
        task2 = service.create_task(
            title="任务2",
            description="描述2",
            priority=TaskPriority.LOW,
            assignee="agent-001",
        )

        assert task1.task_id != task2.task_id


class TestTaskRetrieval:
    """任务查询测试"""

    def test_get_existing_task(self):
        """测试获取已存在的任务"""
        service = TaskService()
        created_task = service.create_task(
            title="测试任务",
            description="测试获取任务",
            priority=TaskPriority.MEDIUM,
            assignee="agent-001",
        )

        retrieved_task = service.get_task(created_task.task_id)

        assert retrieved_task is not None
        assert retrieved_task.task_id == created_task.task_id
        assert retrieved_task.title == "测试任务"

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        service = TaskService()
        task = service.get_task("nonexistent-task-id")

        assert task is None

    def test_list_all_tasks(self):
        """测试列出所有任务"""
        service = TaskService()
        service.create_task("任务1", "描述1", TaskPriority.HIGH, "agent-001")
        service.create_task("任务2", "描述2", TaskPriority.LOW, "agent-002")
        service.create_task("任务3", "描述3", TaskPriority.MEDIUM, "agent-003")

        tasks = service.list_tasks()

        assert len(tasks) == 3

    def test_list_tasks_with_status_filter(self):
        """测试按状态过滤任务"""
        service = TaskService()
        task1 = service.create_task("任务1", "描述1", TaskPriority.HIGH, "agent-001")
        task2 = service.create_task("任务2", "描述2", TaskPriority.HIGH, "agent-002")
        task3 = service.create_task("任务3", "描述3", TaskPriority.HIGH, "agent-003")

        # 更新任务状态
        service.update_task_status(task1.task_id, TaskStatus.IN_PROGRESS)
        service.update_task_status(task2.task_id, TaskStatus.COMPLETED)

        # 过滤进行中的任务
        in_progress_tasks = service.list_tasks(status=TaskStatus.IN_PROGRESS)

        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0].task_id == task1.task_id

    def test_list_tasks_with_assignee_filter(self):
        """测试按分配对象过滤任务"""
        service = TaskService()
        service.create_task("任务1", "描述1", TaskPriority.HIGH, "agent-001")
        service.create_task("任务2", "描述2", TaskPriority.HIGH, "agent-001")
        service.create_task("任务3", "描述3", TaskPriority.HIGH, "agent-002")

        agent1_tasks = service.list_tasks(assignee="agent-001")

        assert len(agent1_tasks) == 2
        assert all(t.assignee == "agent-001" for t in agent1_tasks)

    def test_list_tasks_with_pagination(self):
        """测试任务分页"""
        service = TaskService()
        for i in range(10):
            service.create_task(f"任务{i}", f"描述{i}", TaskPriority.MEDIUM, "agent-001")

        # 获取第一页（5条）
        page1 = service.list_tasks(limit=5, offset=0)
        assert len(page1) == 5

        # 获取第二页（5条）
        page2 = service.list_tasks(limit=5, offset=5)
        assert len(page2) == 5

        # 确保两页内容不同
        page1_ids = {t.task_id for t in page1}
        page2_ids = {t.task_id for t in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_tasks_sorted_by_updated_at(self):
        """测试任务按更新时间降序排列"""
        import time

        service = TaskService()
        task1 = service.create_task("任务1", "描述1", TaskPriority.MEDIUM, "agent-001")
        time.sleep(0.01)  # 确保时间戳不同
        task2 = service.create_task("任务2", "描述2", TaskPriority.MEDIUM, "agent-001")
        time.sleep(0.01)
        task3 = service.create_task("任务3", "描述3", TaskPriority.MEDIUM, "agent-001")

        # 更新 task1，使其成为最新
        service.update_task_status(task1.task_id, TaskStatus.IN_PROGRESS)

        tasks = service.list_tasks()

        # task1 应该在第一位（最新更新）
        assert tasks[0].task_id == task1.task_id


class TestTaskUpdate:
    """任务更新测试"""

    def test_update_task_status(self):
        """测试更新任务状态"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        updated_task = service.update_task_status(
            task.task_id,
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=50,
            current_step="执行中",
        )

        assert updated_task is not None
        assert updated_task.status == TaskStatus.IN_PROGRESS
        assert updated_task.progress_percentage == 50
        assert updated_task.current_step == "执行中"

    def test_update_task_with_logs(self):
        """测试更新任务时添加日志"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        logs = [
            {"level": "INFO", "message": "任务开始", "timestamp": "2025-03-15T12:00:00Z"},
            {"level": "INFO", "message": "执行中", "timestamp": "2025-03-15T12:01:00Z"},
        ]

        updated_task = service.update_task_status(
            task.task_id, status=TaskStatus.IN_PROGRESS, logs=logs
        )

        assert updated_task is not None
        assert len(updated_task.logs) == 2
        assert updated_task.logs[0]["message"] == "任务开始"

    def test_update_nonexistent_task(self):
        """测试更新不存在的任务"""
        service = TaskService()
        updated_task = service.update_task_status(
            "nonexistent-task-id", status=TaskStatus.IN_PROGRESS
        )

        assert updated_task is None

    def test_update_task_sets_completed_at(self):
        """测试完成任务时设置完成时间"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        assert task.completed_at is None

        updated_task = service.update_task_status(task.task_id, TaskStatus.COMPLETED)

        assert updated_task is not None
        assert updated_task.completed_at is not None


class TestTaskCompletion:
    """任务完成测试"""

    def test_complete_task_success(self):
        """测试成功完成任务"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.HIGH, "agent-001")

        result = {"output": "任务完成", "files_created": 5}
        completed_task = service.complete_task(
            task.task_id, result=result, execution_time_ms=1500
        )

        assert completed_task is not None
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.progress_percentage == 100
        assert completed_task.result == result
        assert completed_task.execution_time_ms == 1500
        assert completed_task.completed_at is not None

    def test_complete_nonexistent_task(self):
        """测试完成不存在的任务"""
        service = TaskService()
        completed_task = service.complete_task("nonexistent-task-id", result={})

        assert completed_task is None


class TestTaskFailure:
    """任务失败测试"""

    def test_fail_task(self):
        """测试标记任务失败"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.HIGH, "agent-001")

        failed_task = service.fail_task(
            task.task_id,
            error_code="TIMEOUT",
            error_message="任务执行超时",
            retry_possible=True,
        )

        assert failed_task is not None
        assert failed_task.status == TaskStatus.FAILED
        assert failed_task.error["code"] == "TIMEOUT"
        assert failed_task.error["message"] == "任务执行超时"
        assert failed_task.error["retry_possible"] is True
        assert failed_task.completed_at is not None

    def test_fail_nonexistent_task(self):
        """测试失败标记不存在的任务"""
        service = TaskService()
        failed_task = service.fail_task(
            "nonexistent-task-id", error_code="ERROR", error_message="错误"
        )

        assert failed_task is None


class TestTaskCancellation:
    """任务取消测试"""

    def test_cancel_task_with_reason(self):
        """测试取消任务并提供原因"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        cancelled_task = service.cancel_task(task.task_id, reason="用户取消")

        assert cancelled_task is not None
        assert cancelled_task.status == TaskStatus.CANCELLED
        assert "已取消: 用户取消" in cancelled_task.current_step
        assert cancelled_task.completed_at is not None

    def test_cancel_task_without_reason(self):
        """测试取消任务不提供原因"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        cancelled_task = service.cancel_task(task.task_id)

        assert cancelled_task is not None
        assert cancelled_task.status == TaskStatus.CANCELLED
        assert cancelled_task.current_step == "已取消"

    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务"""
        service = TaskService()
        cancelled_task = service.cancel_task("nonexistent-task-id")

        assert cancelled_task is None


class TestTaskDeletion:
    """任务删除测试"""

    def test_delete_existing_task(self):
        """测试删除已存在的任务"""
        service = TaskService()
        task = service.create_task("待删除任务", "描述", TaskPriority.LOW, "agent-003")

        success = service.delete_task(task.task_id)

        assert success is True
        assert service.get_task(task.task_id) is None

    def test_delete_nonexistent_task(self):
        """测试删除不存在的任务"""
        service = TaskService()
        success = service.delete_task("nonexistent-task-id")

        assert success is False


class TestTaskStatistics:
    """任务统计测试"""

    def test_get_statistics_with_tasks(self):
        """测试获取任务统计（有任务）"""
        service = TaskService()
        service.create_task("任务1", "描述1", TaskPriority.URGENT, "agent-001")
        service.create_task("任务2", "描述2", TaskPriority.HIGH, "agent-002")
        service.create_task("任务3", "描述3", TaskPriority.MEDIUM, "agent-003")

        task1 = service.list_tasks()[0]
        task2 = service.list_tasks()[1]
        service.update_task_status(task1.task_id, TaskStatus.IN_PROGRESS)
        service.update_task_status(task2.task_id, TaskStatus.COMPLETED)

        stats = service.get_statistics()

        assert stats["total"] == 3
        assert stats["by_status"]["pending"] == 1
        assert stats["by_status"]["in_progress"] == 1
        assert stats["by_status"]["completed"] == 1
        assert stats["by_priority"]["urgent"] == 1
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["medium"] == 1

    def test_get_statistics_empty(self):
        """测试获取任务统计（无任务）"""
        service = TaskService()
        stats = service.get_statistics()

        assert stats["total"] == 0
        assert all(count == 0 for count in stats["by_status"].values())
        assert all(count == 0 for count in stats["by_priority"].values())


class TestTaskServiceSingleton:
    """任务服务单例测试"""

    def test_get_task_service_returns_singleton(self):
        """测试获取任务服务单例"""
        service1 = get_task_service()
        service2 = get_task_service()

        # 应该是同一个实例
        assert service1 is service2

    def test_singleton_shares_state(self):
        """测试单例在多次调用间共享状态"""
        service1 = get_task_service()
        task = service1.create_task(
            "测试任务", "描述", TaskPriority.MEDIUM, "agent-001"
        )

        service2 = get_task_service()
        retrieved_task = service2.get_task(task.task_id)

        assert retrieved_task is not None
        assert retrieved_task.task_id == task.task_id


class TestTaskToDict:
    """Task.to_dict() 方法测试"""

    def test_task_to_dict_contains_all_fields(self):
        """测试 to_dict 包含所有字段"""
        service = TaskService()
        task = service.create_task(
            title="测试任务",
            description="测试 to_dict",
            priority=TaskPriority.HIGH,
            assignee="agent-001",
            metadata={"key": "value"},
            requirements=["REQ-001"],
        )

        task_dict = task.to_dict()

        assert "task_id" in task_dict
        assert "title" in task_dict
        assert "description" in task_dict
        assert "priority" in task_dict
        assert "assignee" in task_dict
        assert "deadline" in task_dict
        assert "metadata" in task_dict
        assert "requirements" in task_dict
        assert "status" in task_dict
        assert "progress_percentage" in task_dict
        assert "current_step" in task_dict
        assert "created_at" in task_dict
        assert "updated_at" in task_dict
        assert "completed_at" in task_dict
        assert "result" in task_dict
        assert "error" in task_dict
        assert "logs" in task_dict
        assert "execution_time_ms" in task_dict

    def test_task_to_dict_values_are_correct(self):
        """测试 to_dict 返回的值正确"""
        service = TaskService()
        metadata = {"project": "test"}
        requirements = ["REQ-001", "REQ-002"]

        task = service.create_task(
            title="测试任务",
            description="测试",
            priority=TaskPriority.URGENT,
            assignee="agent-001",
            metadata=metadata,
            requirements=requirements,
        )

        task_dict = task.to_dict()

        assert task_dict["title"] == "测试任务"
        assert task_dict["priority"] == "urgent"
        assert task_dict["assignee"] == "agent-001"
        assert task_dict["metadata"] == metadata
        assert task_dict["requirements"] == requirements
        assert task_dict["status"] == "pending"
        assert task_dict["progress_percentage"] == 0


class TestTaskEdgeCases:
    """任务边界情况测试"""

    def test_update_progress_to_100_percent(self):
        """测试更新进度到 100%"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        updated_task = service.update_task_status(
            task.task_id, status=TaskStatus.IN_PROGRESS, progress_percentage=100
        )

        assert updated_task.progress_percentage == 100

    def test_update_progress_to_0_percent(self):
        """测试更新进度到 0%"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        updated_task = service.update_task_status(
            task.task_id, status=TaskStatus.PENDING, progress_percentage=0
        )

        assert updated_task.progress_percentage == 0

    def test_task_with_empty_metadata(self):
        """测试空元数据的任务"""
        service = TaskService()
        task = service.create_task(
            title="测试任务",
            description="描述",
            priority=TaskPriority.MEDIUM,
            assignee="agent-001",
            metadata={},
        )

        assert task.metadata == {}

    def test_task_with_empty_requirements(self):
        """测试空需求列表的任务"""
        service = TaskService()
        task = service.create_task(
            title="测试任务",
            description="描述",
            priority=TaskPriority.MEDIUM,
            assignee="agent-001",
            requirements=[],
        )

        assert task.requirements == []

    def test_log_accumulation(self):
        """测试日志累积"""
        service = TaskService()
        task = service.create_task("测试任务", "描述", TaskPriority.MEDIUM, "agent-001")

        # 第一次更新添加日志
        logs1 = [{"level": "INFO", "message": "日志1", "timestamp": "2025-03-15T12:00:00Z"}]
        service.update_task_status(task.task_id, logs=logs1)

        # 第二次更新添加更多日志
        logs2 = [{"level": "INFO", "message": "日志2", "timestamp": "2025-03-15T12:01:00Z"}]
        service.update_task_status(task.task_id, logs=logs2)

        updated_task = service.get_task(task.task_id)

        assert len(updated_task.logs) == 2
        assert updated_task.logs[0]["message"] == "日志1"
        assert updated_task.logs[1]["message"] == "日志2"
