"""
Agent Task Service 独立测试脚本

直接运行测试，不依赖 pytest 的数据库配置
"""

import sys
sys.path.insert(0, "d:/projects/opentask/backend")

from opentask.services.agent_task.service import (
    TaskService,
    TaskPriority,
    TaskStatus,
    get_task_service,
)


def test_create_task():
    """测试创建任务"""
    service = TaskService()
    task = service.create_task(
        title="测试任务",
        description="这是一个测试任务",
        priority=TaskPriority.HIGH,
        assignee="agent-001"
    )
    assert task is not None
    assert task.title == "测试任务"
    assert task.status == TaskStatus.PENDING
    print("[PASS] test_create_task")


def test_get_task():
    """测试获取任务"""
    service = TaskService()
    task = service.create_task("测试", "描述", TaskPriority.MEDIUM, "agent-001")
    retrieved = service.get_task(task.task_id)
    assert retrieved is not None
    assert retrieved.task_id == task.task_id
    print("[PASS] test_get_task")


def test_list_tasks():
    """测试列出任务"""
    service = TaskService()
    service.create_task("任务1", "描述1", TaskPriority.HIGH, "agent-001")
    service.create_task("任务2", "描述2", TaskPriority.LOW, "agent-002")
    tasks = service.list_tasks()
    assert len(tasks) == 2
    print("[PASS] test_list_tasks")


def test_update_task_status():
    """测试更新任务状态"""
    service = TaskService()
    task = service.create_task("测试", "描述", TaskPriority.MEDIUM, "agent-001")
    updated = service.update_task_status(
        task.task_id,
        status=TaskStatus.IN_PROGRESS,
        progress_percentage=50
    )
    assert updated.status == TaskStatus.IN_PROGRESS
    assert updated.progress_percentage == 50
    print("[PASS] test_update_task_status")


def test_complete_task():
    """测试完成任务"""
    service = TaskService()
    task = service.create_task("测试", "描述", TaskPriority.HIGH, "agent-001")
    completed = service.complete_task(
        task.task_id,
        result={"output": "完成"},
        execution_time_ms=1000
    )
    assert completed.status == TaskStatus.COMPLETED
    assert completed.progress_percentage == 100
    assert completed.result == {"output": "完成"}
    print("[PASS] test_complete_task")


def test_fail_task():
    """测试任务失败"""
    service = TaskService()
    task = service.create_task("测试", "描述", TaskPriority.MEDIUM, "agent-001")
    failed = service.fail_task(
        task.task_id,
        error_code="ERROR",
        error_message="出错了"
    )
    assert failed.status == TaskStatus.FAILED
    assert failed.error["code"] == "ERROR"
    print("[PASS] test_fail_task")


def test_cancel_task():
    """测试取消任务"""
    service = TaskService()
    task = service.create_task("测试", "描述", TaskPriority.LOW, "agent-001")
    cancelled = service.cancel_task(task.task_id, reason="测试取消")
    assert cancelled.status == TaskStatus.CANCELLED
    print("[PASS] test_cancel_task")


def test_delete_task():
    """测试删除任务"""
    service = TaskService()
    task = service.create_task("测试", "描述", TaskPriority.MEDIUM, "agent-001")
    success = service.delete_task(task.task_id)
    assert success is True
    assert service.get_task(task.task_id) is None
    print("[PASS] test_delete_task")


def test_statistics():
    """测试统计"""
    service = TaskService()
    service.create_task("任务1", "描述1", TaskPriority.HIGH, "agent-001")
    service.create_task("任务2", "描述2", TaskPriority.LOW, "agent-002")
    task3 = service.create_task("任务3", "描述3", TaskPriority.MEDIUM, "agent-003")
    service.update_task_status(task3.task_id, TaskStatus.IN_PROGRESS)

    stats = service.get_statistics()
    assert stats["total"] == 3
    assert stats["by_status"]["pending"] == 2
    assert stats["by_status"]["in_progress"] == 1
    print("[PASS] test_statistics")


def test_singleton():
    """测试单例"""
    service1 = get_task_service()
    service2 = get_task_service()
    assert service1 is service2
    print("[PASS] test_singleton")


def run_all_tests():
    """运行所有测试"""
    tests = [
        test_create_task,
        test_get_task,
        test_list_tasks,
        test_update_task_status,
        test_complete_task,
        test_fail_task,
        test_cancel_task,
        test_delete_task,
        test_statistics,
        test_singleton,
    ]

    print("=" * 50)
    print("Agent Task Service Unit Tests")
    print("=" * 50)

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {e}")
            failed += 1

    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
