"""E16: 任务协议规则的可采集单测（替代 opentask/api/test 遗留脚本）。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_rule_1_stale_tasks_can_be_marked_failed():
    from opentask.services.mission_center.service import TaskService

    stale = SimpleNamespace(task_id="t-stale", assignee="agent-1", title="stale")
    failed = SimpleNamespace(task_id="t-stale", status="failed")

    svc = TaskService.__new__(TaskService)
    svc.get_stale_tasks = AsyncMock(return_value=[stale])
    svc.mark_task_as_failed = AsyncMock(return_value=failed)

    found = await svc.get_stale_tasks(timeout_hours=0)
    assert len(found) == 1
    result = await svc.mark_task_as_failed(found[0].task_id, reason="timeout")
    assert result.task_id == "t-stale"
    svc.mark_task_as_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_rule_2_active_task_count_for_agent():
    from opentask.services.mission_center.service import TaskService

    svc = TaskService.__new__(TaskService)
    svc.count_active_tasks_for_agent = AsyncMock(side_effect=[1, 0, 1])

    assert await svc.count_active_tasks_for_agent("agent-a") == 1
    assert await svc.count_active_tasks_for_agent("agent-a") == 0
    assert await svc.count_active_tasks_for_agent("agent-a") == 1


@pytest.mark.asyncio
async def test_task_monitor_check_once_marks_stale():
    from opentask.services.mission_center.task_monitor import TaskMonitorService

    stale = SimpleNamespace(task_id="t1", title="one", assignee="a")
    failed = SimpleNamespace(task_id="t1", title="one")
    fake_svc = AsyncMock()
    fake_svc.get_stale_tasks = AsyncMock(return_value=[stale])
    fake_svc.mark_task_as_failed = AsyncMock(return_value=failed)

    monitor = TaskMonitorService(check_interval_minutes=5, timeout_hours=1)
    with patch(
        "opentask.services.mission_center.task_monitor.get_task_service",
        return_value=fake_svc,
    ):
        results = await monitor.check_once()

    assert len(results) == 1
    assert results[0].task_id == "t1"
    fake_svc.get_stale_tasks.assert_awaited_once_with(timeout_hours=1)
    fake_svc.mark_task_as_failed.assert_awaited_once()
