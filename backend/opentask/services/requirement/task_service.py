"""任务服务层"""
import logging
import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from opentask.models.task.model import Task, TaskDependency
from opentask.models.task.schema import TaskCreate, TaskUpdate, DocumentSummary
from opentask.models.task.enums import TaskStatus, TaskType
from opentask.services.user_center.rbac_service import RbacService

logger = logging.getLogger(__name__)

# Mission Center 服务（延迟导入以避免循环依赖）


def get_mission_service():
    """获取 Mission Center 任务服务"""
    from opentask.services.mission_center.service import get_task_service
    return get_task_service()


class TaskService:
    """任务服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_task_code(self, requirement_id: str, parent_id: Optional[str] = None) -> str:
        """
        生成任务编码

        规则：
        - 顶级任务：从 1 开始自增 (1, 2, 3, ...)
        - 子任务：父任务编码 + . + 子任务序号 (1.1, 1.2, 2.1, ...)

        Args:
            requirement_id: 需求 ID
            parent_id: 父任务 ID (可选)

        Returns:
            任务编码字符串
        """
        if parent_id:
            # 子任务：获取父任务编码
            parent_task = await self.get_by_id(parent_id)

            # 获取同级子任务数量
            result = await self.db.execute(
                select(Task)
                .where(
                    and_(
                        Task.requirement_id == requirement_id,
                        Task.parent_id == parent_id
                    )
                )
            )
            sibling_count = len(result.scalars().all())

            # 生成子任务编码
            parent_code = parent_task.code or "0"
            return f"{parent_code}.{sibling_count + 1}"
        else:
            # 顶级任务：获取同级任务数量
            result = await self.db.execute(
                select(Task)
                .where(
                    and_(
                        Task.requirement_id == requirement_id,
                        Task.parent_id.is_(None)
                    )
                )
            )
            sibling_count = len(result.scalars().all())

            # 生成顶级任务编码
            return str(sibling_count + 1)

    async def regenerate_task_codes(self, requirement_id: str) -> dict[str, str]:
        """
        为需求下的所有任务重新生成编码

        Args:
            requirement_id: 需求 ID

        Returns:
            任务 ID 到新编码的映射
        """
        # 获取所有任务
        result = await self.db.execute(
            select(Task)
            .where(Task.requirement_id == requirement_id)
            .order_by(Task.created_at.asc())
        )
        all_tasks = list(result.scalars().all())

        # 分离顶级任务和子任务
        top_level_tasks = [t for t in all_tasks if t.parent_id is None]
        child_tasks = {t.parent_id: [] for t in all_tasks if t.parent_id is not None}
        for task in all_tasks:
            if task.parent_id:
                if task.parent_id not in child_tasks:
                    child_tasks[task.parent_id] = []
                child_tasks[task.parent_id].append(task)

        # 为顶级任务生成编码
        code_map = {}
        for idx, task in enumerate(top_level_tasks, 1):
            task.code = str(idx)
            code_map[task.id] = task.code

        # 为子任务生成编码
        for parent_id, children in child_tasks.items():
            # 确保父任务有编码
            if parent_id not in code_map:
                # 父任务可能不在当前需求中，获取其编码
                try:
                    parent_task = await self.get_by_id(parent_id)
                    parent_code = parent_task.code or "0"
                except ValueError:
                    parent_code = "0"
            else:
                parent_code = code_map[parent_id]

            # 为每个子任务生成编码
            for idx, task in enumerate(children, 1):
                task.code = f"{parent_code}.{idx}"
                code_map[task.id] = task.code

        await self.db.commit()
        return code_map

    async def get_by_id(self, task_id: str) -> Task:
        """根据 ID 获取任务"""
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        return task

    async def get_task_documents(self, task_id: str) -> list[DocumentSummary]:
        """
        获取任务关联的文档列表

        Args:
            task_id: 任务 ID

        Returns:
            文档摘要列表
        """
        from opentask.models.document.model import Document

        query = select(Document).where(
            Document.entity_type == "task",
            Document.entity_id == task_id
        ).order_by(Document.created_at.desc())

        result = await self.db.execute(query)
        documents = result.scalars().all()

        return [
            DocumentSummary(
                id=doc.id,
                title=doc.file_name,
                status=doc.status.value,
                # 附件型文档无版本概念，恒为 1（schema 必填字段）
                version=1,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]

    async def get_by_requirement(
        self,
        requirement_id: str,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[str] = None,
        visible_dept_ids: set[str] | None = None,
    ) -> list[Task]:
        """获取需求的任务列表

        visible_dept_ids: 数据范围可见部门集（None=不过滤，空集=SELF 结果恒空）。
        本期按 tasks 表自身 dept_id 过滤（与父需求可见性独立）。
        """
        query = select(Task).where(Task.requirement_id == requirement_id)

        if status:
            query = query.where(Task.status == status)
        if assigned_to:
            query = query.where(Task.assigned_to == assigned_to)

        # 数据范围过滤（visible_dept_ids=None 时原样返回，旧调用零破坏）
        query = RbacService(session=None).apply_data_scope(
            query,
            visible_dept_ids,
            dept_col=Task.dept_id,
        )

        # 按 code 排序（任务需要按顺序依次完成）
        query = query.order_by(Task.code.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, dto: TaskCreate, dept_id: str | None = None) -> Task:
        """创建任务

        dept_id: 创建人主部门 id 快照（None 表示无归属，行保持 NULL）
        """
        # 验证层级限制（最多两级）
        if dto.parent_id:
            parent_task = await self.get_by_id(dto.parent_id)
            if parent_task.parent_id:
                raise ValueError("任务最多支持两级：父任务 -> 子任务")

        # 验证PGE任务数量限制（每个需求最多一个PGE顶级任务）
        from opentask.models.task.enums import TaskFramework
        if hasattr(dto, 'framework') and dto.framework == TaskFramework.PGE and not dto.parent_id:
            # 检查该需求下是否已存在PGE顶级任务
            result = await self.db.execute(
                select(Task)
                .where(
                    and_(
                        Task.requirement_id == dto.requirement_id,
                        Task.framework == TaskFramework.PGE,
                        Task.parent_id.is_(None)
                    )
                )
            )
            existing_pge_task = result.scalar_one_or_none()
            if existing_pge_task:
                raise ValueError("每个需求最多只能创建一个PGE任务")

        # 生成任务编码
        code = await self.generate_task_code(dto.requirement_id, dto.parent_id)

        task = Task(
            id=str(uuid.uuid4()),
            requirement_id=dto.requirement_id,
            parent_id=dto.parent_id,
            title=dto.title,
            description=dto.description,
            task_type=dto.task_type,
            framework=dto.framework if hasattr(dto, 'framework') else None,
            assigned_to=dto.assigned_to,
            input_data=dto.input_data,
            status=TaskStatus.PENDING,
            code=code,
            dept_id=dept_id,  # 部门归属快照：创建时创建人的主部门
        )

        self.db.add(task)
        await self.db.flush()

        # 🆕 同步到 Mission Center（仅顶级任务）
        if not dto.parent_id:
            try:
                mission_service = get_mission_service()
                agent_task = await mission_service.create_task_with_links(
                    title=task.title,
                    description=task.description or "",
                    link_data=[f"task:{task.id}"],
                    context={
                        "requirement_id": task.requirement_id,
                        "task_code": task.code,
                        "task_type": task.task_type
                    },
                    created_by="system",
                    task_type="requirement_task",
                    priority="medium",
                    dept_id=dept_id,  # 部门快照随任务同步到 Mission Center
                )
                # 更新 task 的 agent_task_id
                task.agent_task_id = agent_task.task_id
                logger.info(f"✅ 任务 {task.id} 已同步到 Mission Center: {agent_task.task_id}")
            except Exception as e:
                logger.error(f"❌ 同步任务到 Mission Center 失败: {e}")
                # 继续执行，不阻塞任务创建
                # 可以考虑添加重试机制或发送告警

        # 创建依赖关系
        if dto.depends_on:
            for dep_id in dto.depends_on:
                dependency = TaskDependency(
                    task_id=task.id,
                    depends_on_id=dep_id
                )
                self.db.add(dependency)

        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def update(self, task_id: str, dto: TaskUpdate) -> Task:
        """更新任务"""
        task = await self.get_by_id(task_id)

        # 更新状态
        if dto.status:
            # 状态转换逻辑
            if dto.status == TaskStatus.RUNNING and task.status == TaskStatus.PENDING:
                task.started_at = datetime.utcnow()
            elif dto.status == TaskStatus.COMPLETED:
                task.completed_at = datetime.utcnow()
            elif dto.status == TaskStatus.FAILED:
                task.retry_count += 1

            task.status = dto.status

        # 更新其他字段
        if dto.title is not None:
            task.title = dto.title
        if dto.description is not None:
            task.description = dto.description
        if dto.assigned_to is not None:
            task.assigned_to = dto.assigned_to
        if dto.output_data is not None:
            task.output_data = dto.output_data
        if dto.artifacts is not None:
            task.artifacts = dto.artifacts
        if dto.error_message is not None:
            task.error_message = dto.error_message
        if hasattr(dto, 'parent_id') and dto.parent_id is not None:
            task.parent_id = dto.parent_id

        task.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def delete(self, task_id: str) -> None:
        """删除任务（级联删除所有子任务）"""
        task = await self.get_by_id(task_id)

        # 级联删除所有子任务（需求2026-122）
        result = await self.db.execute(
            select(Task).where(Task.parent_id == task_id)
        )
        child_tasks = result.scalars().all()

        # 递归删除所有子任务
        for child_task in child_tasks:
            await self.delete(child_task.id)  # 递归调用

        # 🆕 同步删除 Mission Center 中的关联任务（需求2026-123）
        if task.agent_task_id:
            try:
                mission_service = get_mission_service()
                await mission_service.delete_task(task.agent_task_id)
                logger.info(f"✅ Mission Center 任务 {task.agent_task_id} 已删除")
            except Exception as e:
                logger.error(f"❌ 删除 Mission Center 任务失败: {e}")
                # 继续执行，不阻塞任务删除

        # 删除当前任务
        await self.db.delete(task)
        await self.db.commit()
        logger.info(f"Deleted task {task_id} and {len(child_tasks)} child tasks")

    async def get_dependencies(self, task_id: str) -> list[Task]:
        """获取任务依赖"""
        result = await self.db.execute(
            select(Task)
            .join(TaskDependency, Task.id == TaskDependency.depends_on_id)
            .where(TaskDependency.task_id == task_id)
        )
        return list(result.scalars().all())

    async def get_dependents(self, task_id: str) -> list[Task]:
        """获取依赖此任务的其他任务"""
        result = await self.db.execute(
            select(Task)
            .join(TaskDependency, Task.id == TaskDependency.task_id)
            .where(TaskDependency.depends_on_id == task_id)
        )
        return list(result.scalars().all())

    async def can_start(self, task_id: str) -> tuple[bool, list[str]]:
        """检查任务是否可以开始 (依赖是否完成)"""
        dependencies = await self.get_dependencies(task_id)
        blocking = []

        for dep in dependencies:
            if dep.status != TaskStatus.COMPLETED:
                blocking.append(dep.title)

        return len(blocking) == 0, blocking

    async def update_dependencies(self, task_id: str, depends_on: list[str]) -> None:
        """更新任务的依赖关系"""
        # 获取现有依赖
        result = await self.db.execute(
            select(TaskDependency).where(TaskDependency.task_id == task_id)
        )
        existing_deps = result.scalars().all()

        # 删除旧依赖
        for dep in existing_deps:
            await self.db.delete(dep)

        # 创建新依赖
        for dep_id in depends_on:
            # 验证依赖任务存在
            try:
                await self.get_by_id(dep_id)
                dependency = TaskDependency(
                    task_id=task_id,
                    depends_on_id=dep_id
                )
                self.db.add(dependency)
            except ValueError:
                # 依赖任务不存在，跳过
                logger.warning(f"依赖任务 {dep_id} 不存在，跳过")

        await self.db.commit()

    async def get_children(self, task_id: str) -> list[Task]:
        """获取子任务列表"""
        result = await self.db.execute(
            select(Task)
            .where(Task.parent_id == task_id)
            .order_by(Task.code.asc())
        )
        return list(result.scalars().all())

    def to_response(self, task: Task, children: list[Task] | None = None, documents: list[DocumentSummary] | None = None) -> dict[str, Any]:
        """转换为响应格式"""
        return {
            "id": task.id,
            "requirement_id": task.requirement_id,
            "parent_id": task.parent_id,
            "code": task.code,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "status": task.status,
            "assigned_to": task.assigned_to,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "input_data": task.input_data,
            "output_data": task.output_data,
            "artifacts": task.artifacts,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "agent_task_id": task.agent_task_id,  # 添加 agent_task_id 字段
            "children": [self.to_response(child, None, None) for child in (children or [])],
            "documents": documents or []
        }
