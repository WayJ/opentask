"""
E16: 本文件为遗留手工脚本（依赖真实 agent_tasks 表、无 pytest fixture）。
已从 pytest 采集路径排除（pytest.ini testpaths=tests）；保留供本地 `python -m` 调试。

测试任务协议的两个核心规则：

规则1: 超时任务自动失败
规则2: 每个 Agent 一次只能认领一个任务
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from opentask.services.mission_center.service import (
    TaskService,
    TaskPriority,
    TaskStatus,
)
from opentask.services.mission_center.task_monitor import get_task_monitor_service


async def test_rule_1_timeout_tasks():
    """测试规则1: 超时任务自动失败"""
    print("\n" + "=" * 60)
    print("测试规则1: 超时任务自动失败")
    print("=" * 60)

    service = TaskService()

    # 创建一个测试任务
    task = await service.create_task(
        title="测试超时任务",
        description="这个任务将被用来测试超时自动失败规则",
        priority=TaskPriority.MEDIUM,
    )

    print(f"\n✅ 创建测试任务: {task.task_id}")

    # 认领任务
    claimed_task = await service.update_task_status(
        task_id=task.task_id,
        status=TaskStatus.ASSIGNED,
        progress_percentage=0,
        current_step="任务已认领",
        assignee="test-agent-1",
    )

    print(f"✅ 任务已认领: {claimed_task.task_id} by test-agent-1")
    print(f"   状态: {claimed_task.status}")
    print(f"   最后更新: {claimed_task.updated_at}")

    # 获取超时任务（假设超时时间为 0 小时，用于测试）
    # 注意：实际配置是 1 小时，这里我们手动标记一个任务为失败来测试
    stale_tasks = await service.get_stale_tasks(timeout_hours=0)
    print(f"\n📊 当前超时任务数量 (0小时超时): {len(stale_tasks)}")

    # 如果有超时任务，标记为失败
    if stale_tasks:
        for stale_task in stale_tasks:
            failed_task = await service.mark_task_as_failed(
                task_id=stale_task.task_id,
                reason=f"任务超时：超过 0 小时未更新进度"
            )
            print(f"⏰ 任务已标记为失败: {failed_task.task_id}")
            print(f"   原认领者: {stale_task.assignee}")
    else:
        print("ℹ️  没有发现超时任务（正常，因为任务刚创建）")

    print("\n✅ 规则1 测试完成")


async def test_rule_2_single_task_limit():
    """测试规则2: 单任务并发限制"""
    print("\n" + "=" * 60)
    print("测试规则2: 单任务并发限制")
    print("=" * 60)

    service = TaskService()

    agent_id = "test-agent-single"

    # 创建第一个任务并认领
    task1 = await service.create_task(
        title="第一个任务",
        description="测试单任务限制的第一个任务",
        priority=TaskPriority.HIGH,
    )

    claimed_task1 = await service.update_task_status(
        task_id=task1.task_id,
        status=TaskStatus.ASSIGNED,
        progress_percentage=0,
        current_step="任务已认领",
        assignee=agent_id,
    )

    print(f"\n✅ 创建并认领第一个任务: {claimed_task1.task_id}")

    # 检查 Agent 的活跃任务数量
    active_count = await service.count_active_tasks_for_agent(agent_id)
    print(f"📊 Agent {agent_id} 当前活跃任务数量: {active_count}")

    assert active_count == 1, "应该有 1 个活跃任务"
    print("✅ 活跃任务数量正确: 1")

    # 尝试认领第二个任务（应该被阻止）
    task2 = await service.create_task(
        title="第二个任务",
        description="测试单任务限制的第二个任务",
        priority=TaskPriority.HIGH,
    )

    print(f"\n✅ 创建第二个任务: {task2.task_id}")

    # 检查活跃任务数量（认领前）
    active_count_before = await service.count_active_tasks_for_agent(agent_id)
    print(f"📊 认领前活跃任务数量: {active_count_before}")

    # 在实际的路由中，这里会抛出异常阻止认领
    # 这里我们只是测试 service 层的计数功能
    print("\n⚠️  注意：在实际 API 中，认领第二个任务时会被阻止")
    print("   错误消息：'Agent 已有 1 个活跃任务，请先完成当前任务后再认领新任务'")

    # 完成第一个任务
    completed_task = await service.update_task_status(
        task_id=task1.task_id,
        status=TaskStatus.COMPLETED,
        progress_percentage=100,
        current_step="任务已完成",
    )

    print(f"\n✅ 完成第一个任务: {completed_task.task_id}")

    # 再次检查活跃任务数量
    active_count_after = await service.count_active_tasks_for_agent(agent_id)
    print(f"📊 完成后活跃任务数量: {active_count_after}")

    assert active_count_after == 0, "完成第一个任务后，应该没有活跃任务"
    print("✅ 活跃任务数量正确: 0")

    # 现在可以认领第二个任务了
    claimed_task2 = await service.update_task_status(
        task_id=task2.task_id,
        status=TaskStatus.ASSIGNED,
        progress_percentage=0,
        current_step="任务已认领",
        assignee=agent_id,
    )

    print(f"\n✅ 成功认领第二个任务: {claimed_task2.task_id}")

    final_count = await service.count_active_tasks_for_agent(agent_id)
    print(f"📊 最终活跃任务数量: {final_count}")

    assert final_count == 1, "应该有 1 个活跃任务"
    print("✅ 活跃任务数量正确: 1")

    print("\n✅ 规则2 测试完成")


async def test_task_monitor_service():
    """测试任务监控服务"""
    print("\n" + "=" * 60)
    print("测试任务监控服务")
    print("=" * 60)

    monitor = get_task_monitor_service()

    # 检查一次
    print("\n🔍 执行一次超时检查...")
    results = await monitor.check_once()

    if results:
        print(f"⏰ 发现并处理了 {len(results)} 个超时任务")
        for task in results:
            print(f"   - {task.task_id}: {task.title}")
    else:
        print("✅ 没有发现超时任务")

    print("\n✅ 任务监控服务测试完成")


async def main():
    """主测试函数"""
    print("\n🧪 任务协议规则测试")
    print("=" * 60)

    try:
        # 测试规则1
        await test_rule_1_timeout_tasks()

        # 测试规则2
        await test_rule_2_single_task_limit()

        # 测试监控服务
        await test_task_monitor_service()

        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
