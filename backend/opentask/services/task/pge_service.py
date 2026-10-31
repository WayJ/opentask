"""PGE 任务服务

负责处理 PGE（Plan-Generation-Evaluation）框架的任务创建、状态计算和提示词生成。
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.task.enums import TaskFramework, TaskStatus, TaskType
from opentask.models.task.model import Task
from opentask.models.task.schema import SUPERPOWER_SKILLS
from opentask.services.task.prompt_renderer import render_pge_prompt

logger = logging.getLogger(__name__)


class PGETaskService:
    """PGE 任务专用服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pge_task(
        self,
        requirement_id: str,
        title: str,
        description: Optional[str],
        framework: TaskFramework,
        required_skills: list[str],
    ) -> Task:
        """
        创建 PGE 任务（含 3 个子任务）

        Args:
            requirement_id: 所属需求 ID
            title: 任务标题
            description: 任务描述
            framework: 任务框架（必须是 PGE）
            required_skills: 必需的 Superpower Skills

        Returns:
            创建的父任务（包含子任务）

        Raises:
            ValueError: 参数验证失败
        """
        # 验证框架类型
        if framework != TaskFramework.PGE:
            raise ValueError(f"当前仅支持 PGE 框架，不支持 {framework}")

        # 验证PGE任务数量限制（需求2026-122）
        from sqlalchemy import and_
        result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.requirement_id == requirement_id,
                    Task.framework == TaskFramework.PGE.value,
                    Task.parent_id.is_(None)
                )
            )
        )
        existing_pge_task = result.scalar_one_or_none()

        # 调试日志：检查现有PGE任务
        logger.info(f"[PGE数量检查] requirement_id={requirement_id}, framework={TaskFramework.PGE.value}")
        logger.info(f"[PGE数量检查] 现有PGE任务: {existing_pge_task.id if existing_pge_task else None}")

        if existing_pge_task:
            logger.error(f"[PGE数量检查] 发现已存在的PGE任务: {existing_pge_task.id}")
            raise ValueError("每个需求最多只能创建一个PGE任务")

        # 验证 Superpower Skills
        valid_skills = set()
        for category_skills in SUPERPOWER_SKILLS.values():
            valid_skills.update(skill["id"] for skill in category_skills)

        invalid_skills = set(required_skills) - valid_skills
        if invalid_skills:
            raise ValueError(f"无效的 Superpower Skills: {invalid_skills}")

        # 部门归属快照：PGE 任务由需求派生，部门跟随所属需求（requirement.dept_id）
        from opentask.models.requirement.model import Requirement
        req_dept = (
            await self.db.execute(
                select(Requirement.dept_id).where(Requirement.id == requirement_id)
            )
        ).scalar_one_or_none()
        requirement_dept_id = str(req_dept) if req_dept is not None else None

        # 创建父任务
        parent_task = Task(
            requirement_id=requirement_id,
            title=title,
            description=description,
            task_type=TaskType.IMPLEMENT,
            framework=framework.value,
            required_skills={"skills": required_skills} if required_skills else None,
            status=TaskStatus.PENDING.value,
            parent_id=None,
            code=None,
            dept_id=requirement_dept_id,
        )

        self.db.add(parent_task)
        await self.db.flush()  # 获取父任务 ID

        # 🆕 同步到 Mission Center（仅顶级任务）
        try:
            from opentask.services.requirement.task_service import get_mission_service
            mission_service = get_mission_service()
            agent_task = await mission_service.create_task_with_links(
                title=parent_task.title,
                description=parent_task.description or "",
                link_data=[f"task:{parent_task.id}"],
                context={
                    "requirement_id": parent_task.requirement_id,
                    "framework": parent_task.framework,
                    "task_type": parent_task.task_type
                },
                created_by="system",
                task_type="pge_task",
                priority="medium",
                dept_id=requirement_dept_id,  # 部门快照跟随所属需求
            )
            # 更新 parent_task 的 agent_task_id
            parent_task.agent_task_id = agent_task.task_id
            logger.info(f"✅ PGE任务 {parent_task.id} 已同步到 Mission Center: {agent_task.task_id}")
        except Exception as e:
            logger.error(f"❌ 同步PGE任务到 Mission Center 失败: {e}")
            # 继续执行，不阻塞任务创建

        # 创建 3 个子任务（部门快照同样跟随所属需求）
        subtasks = [
            Task(
                requirement_id=requirement_id,
                parent_id=parent_task.id,
                code=f"1.1",
                title=f"Plan: {title}",
                description=f"制定详细的实施方案，包括技术选型、架构设计、任务分解",
                task_type=TaskType.PGE_PLAN.value,
                framework=framework.value,
                status=TaskStatus.PENDING.value,
                dept_id=requirement_dept_id,
            ),
            Task(
                requirement_id=requirement_id,
                parent_id=parent_task.id,
                code=f"1.2",
                title=f"Generation: {title}",
                description=f"按照 Plan 方案实现功能，编写代码和测试",
                task_type=TaskType.PGE_GENERATION.value,
                framework=framework.value,
                status=TaskStatus.PENDING.value,
                dept_id=requirement_dept_id,
            ),
            Task(
                requirement_id=requirement_id,
                parent_id=parent_task.id,
                code=f"1.3",
                title=f"Evaluation: {title}",
                description=f"评估 Generation 的产出，检查代码质量、测试覆盖、功能完整性",
                task_type=TaskType.PGE_EVALUATION.value,
                framework=framework.value,
                status=TaskStatus.PENDING.value,
                dept_id=requirement_dept_id,
            ),
        ]

        for subtask in subtasks:
            self.db.add(subtask)

        await self.db.commit()
        await self.db.refresh(parent_task)

        logger.info(f"创建 PGE 任务成功: {parent_task.id}，包含 3 个子任务")
        return parent_task

    async def calculate_parent_status(self, parent_task_id: str) -> TaskStatus:
        """
        根据子任务状态计算父任务状态

        Args:
            parent_task_id: 父任务 ID

        Returns:
            计算后的父任务状态

        状态规则：
        - 全部 PENDING → PENDING
        - 任一 RUNNING 或部分完成 → RUNNING
        - 全部 DONE → DONE
        - 任一 FAILED → FAILED
        """
        # 查询所有子任务
        stmt = select(Task).where(Task.parent_id == parent_task_id)
        result = await self.db.execute(stmt)
        subtasks = result.scalars().all()

        if not subtasks:
            # 没有子任务，保持原状态
            return TaskStatus.PENDING

        # 统计子任务状态
        status_counts = {}
        for subtask in subtasks:
            status = subtask.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # 计算父任务状态
        if status_counts.get(TaskStatus.FAILED.value, 0) > 0:
            parent_status = TaskStatus.FAILED
        elif status_counts.get(TaskStatus.RUNNING.value, 0) > 0:
            parent_status = TaskStatus.RUNNING
        elif status_counts.get(TaskStatus.PENDING.value, 0) == len(subtasks):
            parent_status = TaskStatus.PENDING
        elif status_counts.get(TaskStatus.COMPLETED.value, 0) == len(subtasks):
            parent_status = TaskStatus.COMPLETED
        else:
            # 部分完成，部分进行中
            parent_status = TaskStatus.RUNNING

        # 更新父任务状态
        stmt = select(Task).where(Task.id == parent_task_id)
        result = await self.db.execute(stmt)
        parent_task = result.scalar_one_or_none()

        if parent_task:
            parent_task.status = parent_status.value
            await self.db.commit()
            await self.db.refresh(parent_task)

            logger.info(
                f"父任务 {parent_task_id} 状态更新为 {parent_status.value}，"
                f"子任务状态分布: {status_counts}"
            )

        return parent_status

    async def resolve_task_id(self, task_id: str) -> str:
        """
        解析任务ID（支持短ID查找）

        Args:
            task_id: 任务ID（可以是完整ID或短ID前8位）

        Returns:
            完整的任务ID

        Raises:
            ValueError: 任务不存在或短ID匹配多个任务
        """
        # 如果是UUID格式（包含连字符），尝试直接查找
        if '-' in task_id:
            stmt = select(Task).where(Task.id == task_id)
            result = await self.db.execute(stmt)
            task = result.scalar_one_or_none()
            if task:
                return task.id
            else:
                raise ValueError(f"任务不存在: {task_id}")

        # 否则当作短ID处理（前8位）
        short_id = task_id[:8].lower()

        # 查找匹配的ID（前8位匹配）
        stmt = select(Task).where(Task.id.ilike(f"{short_id}%"))
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        if not tasks:
            raise ValueError(f"未找到匹配的任务: {task_id}")

        if len(tasks) > 1:
            # 找到多个匹配，返回列表
            matching_ids = [task.id for task in tasks]
            raise ValueError(
                f"短ID '{task_id}' 匹配到多个任务，请使用完整ID：\n" +
                "\n".join([f"  - {task_id}" for task_id in matching_ids[:5]]) +
                (f"\n  ... 还有 {len(matching_ids) - 5} 个" if len(matching_ids) > 5 else "")
            )

        # 唯一匹配，返回完整ID
        return tasks[0].id

    async def generate_task_prompt(self, task_id: str) -> str:
        """
        生成任务提示词（使用原有的 pge_prompt 模板）

        Args:
            task_id: 任务 ID

        Returns:
            渲染后的任务提示词

        Raises:
            ValueError: 任务不存在
        """
        # 使用渲染器来填充 pge_prompt 模板
        return await render_pge_prompt(task_id, self.db)
