"""知识库服务层"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from opentask.models.knowledge_base.model import KnowledgeBase
from opentask.models.knowledge.model import Knowledge
from opentask.models.project_knowledge_base import ProjectKnowledgeBase
from opentask.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from opentask.services.user_center.rbac_service import RbacService


class KnowledgeBaseService:
    """知识库服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_knowledge_bases(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        visible_dept_ids: set[str] | None = None,
    ) -> tuple[list[KnowledgeBase], int]:
        """获取知识库列表

        visible_dept_ids: 数据范围可见部门集（None=不过滤；知识库表无 created_by，
        空集（SELF）时结果恒空——知识库均为部门资产）
        """
        query = select(KnowledgeBase)

        # 筛选条件
        if status:
            query = query.where(KnowledgeBase.status == status)
        if keyword:
            query = query.where(KnowledgeBase.name.ilike(f"%{keyword}%"))

        # 数据范围过滤（visible_dept_ids=None 时原样返回，旧调用零破坏）
        query = RbacService(session=None).apply_data_scope(
            query,
            visible_dept_ids,
            dept_col=KnowledgeBase.dept_id,
        )

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        result = await self.db.execute(count_query)
        total = result.scalar()

        # 预加载关联数据
        query = query.options(selectinload(KnowledgeBase.knowledge_items))
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        knowledge_bases = result.scalars().all()

        return list(knowledge_bases), total

    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库详情"""
        query = select(KnowledgeBase).options(
            selectinload(KnowledgeBase.knowledge_items),
            selectinload(KnowledgeBase.projects)
        ).where(KnowledgeBase.id == kb_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_knowledge_base(
        self,
        data: KnowledgeBaseCreate,
        dept_id: str | None = None,
    ) -> KnowledgeBase:
        """创建知识库

        dept_id: 创建人主部门 id 快照（None 表示无归属，行保持 NULL）
        """
        kb = KnowledgeBase(**data.model_dump())
        kb.dept_id = dept_id  # 部门归属快照：创建时创建人的主部门
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def update_knowledge_base(
        self,
        kb_id: str,
        data: KnowledgeBaseUpdate
    ) -> Optional[KnowledgeBase]:
        """更新知识库"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_knowledge_base(kb_id)

        query = (
            update(KnowledgeBase)
            .where(KnowledgeBase.id == kb_id)
            .values(**update_data)
            .returning(KnowledgeBase)
        )
        result = await self.db.execute(query)
        await self.db.commit()

        if result.rowcount == 0:
            return None

        return await self.get_knowledge_base(kb_id)

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库"""
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return False

        await self.db.delete(kb)
        await self.db.commit()
        return True

    async def associate_project(
        self,
        kb_id: str,
        project_id: str
    ) -> ProjectKnowledgeBase:
        """关联项目到知识库"""
        association = ProjectKnowledgeBase(
            knowledge_base_id=kb_id,
            project_id=project_id
        )
        self.db.add(association)
        await self.db.commit()
        await self.db.refresh(association)
        return association

    async def disassociate_project(
        self,
        kb_id: str,
        project_id: str
    ) -> bool:
        """取消项目关联"""
        query = select(ProjectKnowledgeBase).where(
            ProjectKnowledgeBase.knowledge_base_id == kb_id,
            ProjectKnowledgeBase.project_id == project_id
        )
        result = await self.db.execute(query)
        association = result.scalar_one_or_none()
        if not association:
            return False

        await self.db.delete(association)
        await self.db.commit()
        return True

    async def get_associated_projects(self, kb_id: str):
        """获取知识库关联的项目列表"""
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return []

        return kb.projects
