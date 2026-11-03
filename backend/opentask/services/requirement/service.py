"""需求服务"""
# 触发重载测试
import logging
from typing import Any
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from opentask.models.task.model import Task

from opentask.models.requirement.model import Requirement, Event, RequirementRepo, RepoConfig
from opentask.models.requirement.schema import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
    RequirementWithEvents,
    RequirementListResponse,
    RequirementStatistics,
    TimelineResponse,
    AssignRequest,
    DocumentSummary,
)
from opentask.models.requirement.enums import RequirementStatus, Priority, EventType
from opentask.services.user_center.rbac_service import RbacService

logger = logging.getLogger(__name__)

class RequirementService:
    """需求服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, dto: RequirementCreate, dept_id: str | None = None) -> Requirement:
        """
        创建需求

        Args:
            dto: 创建需求 DTO
            dept_id: 创建人主部门 id 快照（None 表示无归属，行保持 NULL）

        Returns:
            创建的需求
        """
        from opentask.models.requirement.model import RequirementCodeSequence
        from datetime import datetime

        # 生成需求编码
        current_year = datetime.now().year

        # 获取或创建当前年份的序列记录
        result = await self.db.execute(
            select(RequirementCodeSequence).where(RequirementCodeSequence.year == current_year)
        )
        code_sequence = result.scalar_one_or_none()

        if code_sequence is None:
            # 如果当前年份没有序列记录，创建一个
            code_sequence = RequirementCodeSequence(year=current_year, sequence=0)
            self.db.add(code_sequence)
            await self.db.flush()

        # 递增序列号
        code_sequence.sequence += 1
        code = f"需求{current_year}-{code_sequence.sequence}"

        requirement = Requirement(
            title=dto.title,
            code=code,
            description=dto.description,
            priority=dto.priority,
            tags=dto.tags,
            status=RequirementStatus.PLANNING,
            created_by=dto.created_by,
            project_id=dto.project_id,
            dept_id=dept_id,  # 部门归属快照：创建时创建人的主部门
        )
        self.db.add(requirement)
        await self.db.flush()

        # TODO: 记录创建事件（需要先实现 event_store 服务）
        # await self.event_store.append_event(
        #     requirement_id=requirement.id,
        #     event_type=EventType.REQUIREMENT_CREATED,
        #     data={
        #         "title": dto.title,
        #         "code": code,
        #         "description": dto.description,
        #         "priority": dto.priority.value if dto.priority else None,
        #         "project_id": dto.project_id,
        #     },
        #     actor=dto.created_by or "system",
        #     snapshot={
        #         "status": RequirementStatus.PLANNING.value,
        #         "code": code,
        #         "title": requirement.title,
        #         "assignee": None,
        #         "project_id": dto.project_id,
        #     },
        # )
        await self.db.commit()

        logger.info(f"Created requirement: {requirement.id} with code: {code}")

        # 重新查询并预加载 project 关联，避免返回时的懒加载问题
        result = await self.db.execute(
            select(Requirement).options(selectinload(Requirement.project)).where(Requirement.id == requirement.id)
        )
        requirement = result.scalar_one()

        return requirement

    async def get_list(
        self,
        status: RequirementStatus | None = None,
        priority: Priority | None = None,
        assignee_id: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
        visible_dept_ids: set[str] | None = None,
        user_id: str | None = None,
    ) -> RequirementListResponse:
        """
        获取需求列表

        Args:
            status: 状态过滤
            priority: 优先级过滤
            assignee_id: 负责人过滤
            project_id: 项目 ID 过滤
            page: 页码
            page_size: 每页数量
            visible_dept_ids: 数据范围可见部门集（None=不过滤，空集=SELF）
            user_id: 当前用户 ID（配合可见部门集实现"或本人创建"）

        Returns:
            需求列表
        """
        query = select(Requirement).options(selectinload(Requirement.project))

        # 应用过滤条件
        conditions = []
        if status:
            conditions.append(Requirement.status == status)
        if priority:
            conditions.append(Requirement.priority == priority)
        if assignee_id:
            conditions.append(Requirement.assignee_id == assignee_id)
        if project_id == "":
            # 空字符串表示筛选未归类的需求（project_id 为 null）
            conditions.append(Requirement.project_id.is_(None))
        elif project_id:
            # 其他值表示筛选特定项目的需求
            conditions.append(Requirement.project_id == project_id)

        if conditions:
            query = query.where(*conditions)

        # 数据范围过滤（visible_dept_ids=None 时 apply_data_scope 原样返回，旧调用零破坏）
        query = RbacService(session=None).apply_data_scope(
            query,
            visible_dept_ids,
            dept_col=Requirement.dept_id,
            creator_col=Requirement.created_by,
            user_id=user_id,
        )

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # 分页
        query = query.order_by(Requirement.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        requirements = list(result.scalars().all())

        return RequirementListResponse(
            data=[self.to_response(r) for r in requirements],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_by_id(self, requirement_id: str, include_documents: bool = True) -> Requirement:
        """
        获取单个需求

        Args:
            requirement_id: 需求 ID
            include_documents: 是否包含关联文档

        Returns:
            需求

        Raises:
            HTTPException: 需求不存在
        """
        result = await self.db.execute(
            select(Requirement).options(selectinload(Requirement.project)).where(Requirement.id == requirement_id)
        )
        requirement = result.scalar_one_or_none()

        if not requirement:
            raise HTTPException(status_code=404, detail=f"Requirement {requirement_id} not found")

        return requirement

    async def get_by_code(self, code: str) -> Requirement:
        """
        通过需求编号获取单个需求

        Args:
            code: 需求编号（如 "需求2026-73"）

        Returns:
            需求

        Raises:
            HTTPException: 需求不存在
        """
        result = await self.db.execute(
            select(Requirement).options(selectinload(Requirement.project)).where(Requirement.code == code)
        )
        requirement = result.scalar_one_or_none()

        if not requirement:
            raise HTTPException(status_code=404, detail=f"Requirement with code '{code}' not found")

        return requirement

    async def get_requirement_documents(self, requirement_id: str) -> list[DocumentSummary]:
        """
        获取需求关联的文档列表

        Args:
            requirement_id: 需求 ID

        Returns:
            文档摘要列表
        """
        from opentask.models.document.model import Document

        query = select(Document).where(
            Document.entity_type == "requirement",
            Document.entity_id == requirement_id
        ).order_by(Document.created_at.desc())

        result = await self.db.execute(query)
        documents = result.scalars().all()

        return [
            DocumentSummary(
                id=doc.id,
                file_name=doc.file_name,
                status=doc.status.value,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]

    async def get_with_events(self, requirement_id: str) -> RequirementWithEvents:
        """
        获取需求详情（包含事件）

        Args:
            requirement_id: 需求 ID

        Returns:
            包含事件的需求
        """
        requirement = await self.get_by_id(requirement_id)
        # TODO: 获取事件（需要先实现 event_store 服务）
        # events = await self.event_store.get_events(requirement_id)
        events = []

        return RequirementWithEvents(
            **self.to_response(requirement).model_dump(),
            events=[],  # [self.event_store.to_response(e) for e in events],
        )

    async def update(self, requirement_id: str, dto: RequirementUpdate, actor: str | None = None) -> Requirement:
        """
        更新需求

        Args:
            requirement_id: 需求 ID
            dto: 更新 DTO
            actor: 操作者

        Returns:
            更新后的需求

        Raises:
            HTTPException: 需求不存在
        """
        from opentask.models.requirement.enums import RequirementStatus
        from opentask.models.task.enums import TaskStatus
        from opentask.services.requirement.task_service import TaskService

        requirement = await self.get_by_id(requirement_id)

        # 记录旧状态，用于后续判断
        old_status = requirement.status

        # 更新需求字段
        update_data = dto.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(requirement, field, value)

        await self.db.commit()

        # 如果需求状态更新为完成，自动结束该需求下的所有任务
        if hasattr(dto, 'status') and dto.status == RequirementStatus.COMPLETED and old_status != RequirementStatus.COMPLETED:
            task_service = TaskService(self.db)
            await self._complete_all_tasks(requirement_id, task_service)

        # 重新查询以获取预加载的关系（refresh不会预加载关系）
        requirement = await self.get_by_id(requirement_id)

        logger.info(f"Updated requirement: {requirement_id} by {actor or 'system'}")
        return requirement

    async def _complete_all_tasks(self, requirement_id: str, task_service: 'TaskService') -> None:
        """
        自动结束需求下的所有任务

        Args:
            requirement_id: 需求 ID
            task_service: 任务服务实例
        """
        from opentask.models.task.enums import TaskStatus
        from sqlalchemy import select, and_

        # 获取该需求下所有未完成的任务
        result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.requirement_id == requirement_id,
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                )
            )
        )
        tasks_to_complete = result.scalars().all()

        # 批量更新任务状态为完成
        for task in tasks_to_complete:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            logger.info(f"Auto-completed task {task.id} (requirement {requirement_id} completed)")

        await self.db.commit()
        logger.info(f"Auto-completed {len(tasks_to_complete)} tasks for requirement {requirement_id}")

    async def delete(self, requirement_id: str) -> None:
        """
        删除需求

        Args:
            requirement_id: 需求 ID
        """
        requirement = await self.get_by_id(requirement_id)
        await self.db.delete(requirement)
        await self.db.commit()

        logger.info(f"Deleted requirement: {requirement_id}")

    async def assign(self, requirement_id: str, dto: AssignRequest, actor: str | None = None) -> Requirement:
        """
        分配需求

        Args:
            requirement_id: 需求 ID
            dto: 分配请求
            actor: 操作者

        Returns:
            更新后的需求
        """
        requirement = await self.get_by_id(requirement_id)

        # TODO: 记录分配事件（需要先实现 event_store 服务）
        # await self.event_store.append_event(
        #     requirement_id=requirement.id,
        #     event_type=EventType.ASSIGNED,
        #     data={
        #         "previous_assignee": requirement.assignee_id,
        #         "new_assignee": dto.assignee_id,
        #     },
        #     actor=actor or "system",
        #     snapshot={"assignee": dto.assignee_id},
        # )

        requirement.assignee_id = dto.assignee_id
        await self.db.commit()

        # 重新查询以获取预加载的关系（refresh不会预加载关系）
        requirement = await self.get_by_id(requirement_id)

        logger.info(f"Assigned requirement {requirement_id} to {dto.assignee_id}")
        return requirement

    async def get_timeline(self, requirement_id: str) -> TimelineResponse:
        """
        获取需求时间线

        Args:
            requirement_id: 需求 ID

        Returns:
            时间线响应
        """
        await self.get_by_id(requirement_id)  # 确保存在
        # TODO: 获取事件（需要先实现 event_store 服务）
        # events = await self.event_store.get_events(requirement_id)
        # time_in_states = await self.event_store.calculate_time_in_states(requirement_id)
        events = []
        time_in_states = {}

        return TimelineResponse(
            requirement_id=requirement_id,
            events=[],  # [self.event_store.to_response(e) for e in events],
            time_in_states=time_in_states,
        )

    async def get_statistics(self) -> RequirementStatistics:
        """
        获取需求统计

        Returns:
            统计信息
        """
        # 总数
        total_result = await self.db.execute(select(func.count()).select_from(Requirement))
        total = total_result.scalar_one()

        # 按状态统计
        by_status_result = await self.db.execute(
            select(Requirement.status, func.count(Requirement.id))
            .group_by(Requirement.status)
        )
        by_status = {getattr(status, "value", status): count for status, count in by_status_result.all()}

        # 按优先级统计
        by_priority_result = await self.db.execute(
            select(Requirement.priority, func.count(Requirement.id))
            .group_by(Requirement.priority)
        )
        by_priority = {
            (getattr(priority, "value", priority) if priority else "unknown"): count
            for priority, count in by_priority_result.all()
        }

        return RequirementStatistics(
            total=total,
            by_status=by_status,
            by_priority=by_priority,
        )

    async def search(self, query: str, limit: int = 20) -> list[RequirementResponse]:
        """
        搜索需求

        Args:
            query: 搜索关键词
            limit: 结果数量限制

        Returns:
            匹配的需求列表
        """
        result = await self.db.execute(
            select(Requirement).options(selectinload(Requirement.project))
            .where(
                or_(
                    Requirement.title.contains(query),
                    Requirement.description.contains(query),
                )
            )
            .order_by(Requirement.created_at.desc())
            .limit(limit)
        )
        requirements = list(result.scalars().all())
        return [self.to_response(r) for r in requirements]

    def to_response(self, requirement: Requirement, documents: list[DocumentSummary] | None = None) -> RequirementResponse:
        """转换为响应 Schema"""
        # 获取项目名称（如果有 project relationship）
        project_name = None
        if requirement.project:
            project_name = requirement.project.name

        # 将字符串转换为枚举类型（修复 Pydantic 验证错误）
        # 数据库中存储的是字符串，但 Pydantic 期望枚举类型
        status_enum = requirement.status
        if isinstance(requirement.status, str):
            try:
                status_enum = RequirementStatus(requirement.status)
            except ValueError:
                # 如果字符串值不匹配任何枚举，使用默认值
                logger.warning(f"Invalid status value: {requirement.status}, using PLANNING as default")
                status_enum = RequirementStatus.PLANNING

        priority_enum = requirement.priority
        if requirement.priority is not None and isinstance(requirement.priority, str):
            try:
                priority_enum = Priority(requirement.priority)
            except ValueError:
                # 如果字符串值不匹配任何枚举，设为 None
                logger.warning(f"Invalid priority value: {requirement.priority}, setting to None")
                priority_enum = None

        return RequirementResponse(
            id=requirement.id,
            code=requirement.code,
            title=requirement.title,
            description=requirement.description,
            status=status_enum,
            priority=priority_enum,
            tags=requirement.tags or [],
            created_at=requirement.created_at,
            updated_at=requirement.updated_at,
            created_by=requirement.created_by,
            assignee_id=requirement.assignee_id,
            project_id=requirement.project_id,
            project_name=project_name,
            documents=documents or [],
        )

    async def get_comments_with_user_info(self, requirement_id: str, page: int = 1, page_size: int = 20) -> dict:
        """
        获取需求的评论（分页），包含用户信息

        Args:
            requirement_id: 需求 ID
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            包含用户信息的评论列表（分页）
        """
        from opentask.models.requirement.model import Comment
        from opentask.models.user.model import UserModel
        from opentask.models.requirement.schema import UserInfo
        from sqlalchemy import func

        # 获取总数
        count_query = select(func.count()).select_from(
            select(Comment)
            .where(Comment.requirement_id == requirement_id)
            .where(Comment.is_deleted == False)
            .subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # 查询评论（倒序排列，最新的在前）
        result = await self.db.execute(
            select(Comment)
            .where(Comment.requirement_id == requirement_id)
            .where(Comment.is_deleted == False)
            .order_by(Comment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        comments = result.scalars().all()

        # 收集所有唯一的 user_id
        user_ids = list(set([UUID(c.user_id) for c in comments if c.user_id]))

        # 批量查询用户信息
        user_info_map = {}
        if user_ids:
            try:
                user_result = await self.db.execute(
                    select(UserModel).where(UserModel.id.in_(user_ids))
                )
                users = user_result.scalars().all()

                user_info_map = {
                    str(user.id): UserInfo(
                        id=str(user.id),
                        name=user.name,
                        sso_name=getattr(user, 'sso_name', None),
                        sso_account=getattr(user, 'sso_account', None)
                    )
                    for user in users
                }
            except Exception as e:
                logger.error(f"Error querying users for comments: {e}")
                import traceback
                traceback.print_exc()

        # 构建响应，添加用户信息
        rows = []
        for comment in comments:
            comment_dict = {
                "id": comment.id,
                "requirement_id": comment.requirement_id,
                "user_id": comment.user_id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
            }
            # 如果找到用户信息，添加到响应中
            if comment.user_id and str(comment.user_id) in user_info_map:
                comment_dict["user_info"] = user_info_map[str(comment.user_id)].model_dump()

            rows.append(comment_dict)

        # 计算总页数
        total_pages = (total + page_size - 1) // page_size

        return {
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
