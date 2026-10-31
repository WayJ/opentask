"""知识文档服务"""
import logging
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.knowledge.model import Knowledge
from opentask.models.knowledge.enums import KnowledgeStatus, KnowledgeVisibility
from opentask.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识文档服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_knowledges(
        self,
        knowledge_base_id: Optional[str] = None,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Knowledge], int]:
        """获取知识文档列表"""
        # 构建查询条件
        conditions = [Knowledge.is_deleted == False]

        if knowledge_base_id:
            conditions.append(Knowledge.knowledge_base_id == knowledge_base_id)

        if category_id:
            conditions.append(Knowledge.category_id == category_id)

        if status:
            conditions.append(Knowledge.status == status)

        if keyword:
            conditions.append(
                or_(
                    Knowledge.title.contains(keyword),
                    Knowledge.content.contains(keyword),
                )
            )

        # 查询总数
        count_query = select(func.count(Knowledge.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 查询数据
        query = (
            select(Knowledge)
            .where(and_(*conditions))
            .order_by(Knowledge.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        knowledges = list(result.scalars().all())

        return knowledges, total

    async def get_knowledge(self, knowledge_id: str) -> Optional[Knowledge]:
        """获取知识文档详情"""
        query = select(Knowledge).where(
            and_(Knowledge.id == knowledge_id, Knowledge.is_deleted == False)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_knowledge_by_slug(self, slug: str) -> Optional[Knowledge]:
        """通过 slug 获取知识文档"""
        query = select(Knowledge).where(
            and_(Knowledge.slug == slug, Knowledge.is_deleted == False)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_knowledge(self, data: KnowledgeCreate, created_by: Optional[str] = None) -> Knowledge:
        """创建知识文档"""
        # 生成 slug
        slug = self._generate_slug(data.title)

        knowledge = Knowledge(
            id=str(uuid4()),
            knowledge_base_id=data.knowledge_base_id,
            title=data.title,
            slug=slug,
            content=data.content,
            category_id=data.category_id,
            visibility=data.visibility or KnowledgeVisibility.INTERNAL,
            status=KnowledgeStatus.DRAFT,
            version=1,
            created_by=created_by,
        )

        self.db.add(knowledge)
        await self.db.commit()
        await self.db.refresh(knowledge)

        logger.info(f"创建知识文档: {knowledge.id} - {knowledge.title}")
        return knowledge

    async def update_knowledge(
        self,
        knowledge_id: str,
        data: KnowledgeUpdate,
        updated_by: Optional[str] = None,
    ) -> Optional[Knowledge]:
        """更新知识文档"""
        knowledge = await self.get_knowledge(knowledge_id)
        if not knowledge:
            return None

        # 更新字段
        if data.title is not None:
            knowledge.title = data.title
            knowledge.slug = self._generate_slug(data.title)

        if data.content is not None:
            knowledge.content = data.content

        if data.category_id is not None:
            knowledge.category_id = data.category_id

        if data.status is not None:
            knowledge.status = data.status

        if data.visibility is not None:
            knowledge.visibility = data.visibility

        knowledge.updated_by = updated_by
        knowledge.version += 1

        await self.db.commit()
        await self.db.refresh(knowledge)

        logger.info(f"更新知识文档: {knowledge.id} - {knowledge.title}")
        return knowledge

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识文档（软删除）"""
        knowledge = await self.get_knowledge(knowledge_id)
        if not knowledge:
            return False

        knowledge.is_deleted = True
        await self.db.commit()

        logger.info(f"删除知识文档: {knowledge_id}")
        return True

    async def increment_view_count(self, knowledge_id: str) -> bool:
        """增加浏览次数"""
        knowledge = await self.get_knowledge(knowledge_id)
        if not knowledge:
            return False

        knowledge.view_count += 1
        await self.db.commit()
        return True

    async def increment_like_count(self, knowledge_id: str) -> bool:
        """增加点赞数"""
        knowledge = await self.get_knowledge(knowledge_id)
        if not knowledge:
            return False

        knowledge.like_count += 1
        await self.db.commit()
        return True

    def _generate_slug(self, title: str) -> str:
        """生成 URL 友好的 slug"""
        # 简单实现：将标题转为小写，空格替换为连字符
        # TODO: 可以使用更复杂的 slug 生成库
        slug = title.lower().strip()
        slug = slug.replace(" ", "-")
        # 移除特殊字符
        slug = "".join(c for c in slug if c.isalnum() or c in "-_")
        return slug
