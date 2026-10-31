"""知识分类服务"""
import logging
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.knowledge_category.model import KnowledgeCategory

logger = logging.getLogger(__name__)


class KnowledgeCategoryService:
    """知识分类服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_categories(
        self, parent_id: Optional[int] = None
    ) -> List[KnowledgeCategory]:
        """获取分类列表"""
        conditions = []

        if parent_id is not None:
            if parent_id == 0:
                # 获取根分类
                conditions.append(KnowledgeCategory.parent_id.is_(None))
            else:
                conditions.append(KnowledgeCategory.parent_id == parent_id)

        query = select(KnowledgeCategory)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(KnowledgeCategory.sort_order)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_category_tree(self) -> List[dict]:
        """获取分类树"""
        # 获取所有分类
        query = select(KnowledgeCategory).order_by(
            KnowledgeCategory.sort_order, KnowledgeCategory.id
        )
        result = await self.db.execute(query)
        categories = list(result.scalars().all())

        # 构建树形结构
        def build_tree(parent_id=None):
            children = []
            for category in categories:
                if (
                    parent_id is None
                    and category.parent_id is None
                ) or (category.parent_id == parent_id):
                    children.append(
                        {
                            "id": category.id,
                            "name": category.name,
                            "icon": category.icon,
                            "sortOrder": category.sort_order,
                            "parentId": category.parent_id,
                            "children": build_tree(category.id),
                        }
                    )
            return children

        return build_tree()

    async def get_category(self, category_id: int) -> Optional[KnowledgeCategory]:
        """获取分类详情"""
        query = select(KnowledgeCategory).where(KnowledgeCategory.id == category_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_category(
        self,
        name: str,
        icon: Optional[str] = None,
        sort_order: int = 0,
        parent_id: Optional[int] = None,
    ) -> KnowledgeCategory:
        """创建分类"""
        category = KnowledgeCategory(
            name=name,
            icon=icon,
            sort_order=sort_order,
            parent_id=parent_id if parent_id and parent_id > 0 else None,
        )

        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)

        logger.info(f"创建知识分类: {category.id} - {category.name}")
        return category

    async def update_category(
        self,
        category_id: int,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        sort_order: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Optional[KnowledgeCategory]:
        """更新分类"""
        category = await self.get_category(category_id)
        if not category:
            return None

        if name is not None:
            category.name = name
        if icon is not None:
            category.icon = icon
        if sort_order is not None:
            category.sort_order = sort_order
        if parent_id is not None:
            category.parent_id = parent_id if parent_id > 0 else None

        await self.db.commit()
        await self.db.refresh(category)

        logger.info(f"更新知识分类: {category_id}")
        return category

    async def delete_category(self, category_id: int) -> bool:
        """删除分类"""
        category = await self.get_category(category_id)
        if not category:
            return False

        # 检查是否有子分类
        children = await self.get_categories(parent_id=category_id)
        if children:
            raise ValueError("该分类下有子分类，无法删除")

        self.db.delete(category)
        await self.db.commit()

        logger.info(f"删除知识分类: {category_id}")
        return True
