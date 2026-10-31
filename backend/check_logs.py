#!/usr/bin/env python3
"""检查数据库中 logs 字段的格式"""
import sys
sys.path.insert(0, 'backend')

from opentask.repositories.mission_center_repository import AgentTaskRepository
from opentask.repositories.base import SessionCreator
import asyncio

async def check_logs_format():
    """检查 logs 字段格式"""
    async with SessionCreator() as session:
        repo = AgentTaskRepository()
        tasks = await repo.list_tasks(session=session, limit=10, offset=0)

        print(f"找到 {len(tasks)} 个任务:\n")

        for task in tasks:
            print(f"任务: {task.task_id}")
            print(f"  标题: {task.title}")
            print(f"  状态: {task.status}")
            print(f"  logs 类型: {type(task.logs)}")
            print(f"  logs 内容: {task.logs}")
            print()

if __name__ == "__main__":
    asyncio.run(check_logs_format())
