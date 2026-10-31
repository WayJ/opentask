"""
任务监控服务 - 定期检查超时任务并处理

规则1: 超时任务自动失败
对于认领后 1 小时内没有更新进度的任务，系统自动将其标记为失败状态
"""

import asyncio
import logging
from datetime import timedelta

from opentask.services.mission_center.service import get_task_service

logger = logging.getLogger(__name__)


class TaskMonitorService:
    """任务监控服务 - 定期检查并处理超时任务"""

    def __init__(self, check_interval_minutes: int = 5, timeout_hours: int = 1):
        """
        初始化任务监控服务

        Args:
            check_interval_minutes: 检查间隔（分钟），默认 5 分钟
            timeout_hours: 超时时间（小时），默认 1 小时
        """
        self.check_interval_minutes = check_interval_minutes
        self.timeout_hours = timeout_hours
        self._running = False
        self._task = None

    async def start(self):
        """启动监控服务"""
        if self._running:
            logger.warning("任务监控服务已在运行中")
            return

        self._running = True
        logger.info(f"🔍 任务监控服务已启动 (检查间隔: {self.check_interval_minutes}分钟, 超时时间: {self.timeout_hours}小时)")

        # 创建后台任务
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """停止监控服务"""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 任务监控服务已停止")

    async def _monitor_loop(self):
        """监控循环"""
        service = get_task_service()

        while self._running:
            try:
                # 检查超时任务
                stale_tasks = await service.get_stale_tasks(timeout_hours=self.timeout_hours)

                if stale_tasks:
                    logger.info(f"📊 发现 {len(stale_tasks)} 个超时任务")

                    for task in stale_tasks:
                        try:
                            # 标记任务为失败
                            failed_task = await service.mark_task_as_failed(
                                task_id=task.task_id,
                                reason=f"任务超时：超过 {self.timeout_hours} 小时未更新进度"
                            )

                            if failed_task:
                                logger.warning(
                                    f"⏰ 任务 {task.task_id} 已超时并标记为失败 "
                                    f"(原认领者: {task.assignee}, "
                                    f"最后更新: {task.updated_at})"
                                )

                                # TODO: 可以通过 WebSocket 通知原认领者任务已超时
                                # await notify_task_timeout(task)

                        except Exception as e:
                            logger.error(f"❌ 处理超时任务 {task.task_id} 失败: {e}")

                elif self._running:
                    logger.debug("✅ 没有发现超时任务")

            except Exception as e:
                logger.error(f"❌ 任务监控检查失败: {e}")

            # 等待下一次检查
            if self._running:
                await asyncio.sleep(self.check_interval_minutes * 60)

    async def check_once(self):
        """执行一次检查（用于手动触发）"""
        service = get_task_service()
        stale_tasks = await service.get_stale_tasks(timeout_hours=self.timeout_hours)

        results = []
        for task in stale_tasks:
            failed_task = await service.mark_task_as_failed(
                task_id=task.task_id,
                reason=f"任务超时：超过 {self.timeout_hours} 小时未更新进度"
            )
            if failed_task:
                results.append(failed_task)
                logger.warning(
                    f"⏰ 任务 {task.task_id} 已超时并标记为失败 "
                    f"(原认领者: {task.assignee})"
                )

        return results


# 全局单例
_task_monitor_service: TaskMonitorService | None = None


def get_task_monitor_service(
    check_interval_minutes: int = 5,
    timeout_hours: int = 1
) -> TaskMonitorService:
    """
    获取任务监控服务单例

    Args:
        check_interval_minutes: 检查间隔（分钟），默认 5 分钟
        timeout_hours: 超时时间（小时），默认 1 小时

    Returns:
        TaskMonitorService 实例
    """
    global _task_monitor_service
    if _task_monitor_service is None:
        _task_monitor_service = TaskMonitorService(
            check_interval_minutes=check_interval_minutes,
            timeout_hours=timeout_hours
        )
    else:
        # 如果服务已创建，更新其配置
        _task_monitor_service.check_interval_minutes = check_interval_minutes
        _task_monitor_service.timeout_hours = timeout_hours
    return _task_monitor_service
