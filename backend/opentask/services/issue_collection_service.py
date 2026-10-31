"""Issue Collection 服务层"""
import logging
import json
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, or_, and_, text
from sqlalchemy.orm import selectinload, joinedload

from opentask.models.issue_collection.model import IssueCollection
from opentask.models.issue_collection.schema import (
    IssueCollectionCreate,
    IssueCollectionUpdate,
    CollectionStatistics,
)
from opentask.models.issue_collection.enums import CollectionStatus
from opentask.models.issue.model import Issue
from opentask.models.issue.enums import IssueStatus, IssueType, IssuePriority


class IssueCollectionService:
    """问题集服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # CRUD 操作
    # ========================================================================

    async def get_collections(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        creator_id: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[IssueCollection], int]:
        """获取问题集列表"""
        # 使用 joinedload 预加载创建人数据
        query = (
            select(IssueCollection)
            .options(joinedload(IssueCollection.creator))
        )

        # 筛选条件
        if status:
            query = query.where(IssueCollection.status == status)
        if creator_id:
            query = query.where(IssueCollection.creator_id == creator_id)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    IssueCollection.title.ilike(search_pattern),
                    IssueCollection.description.ilike(search_pattern),
                )
            )

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        result = await self.db.execute(count_query)
        total = result.scalar()

        # 排序
        sort_column = getattr(IssueCollection, sort_by, IssueCollection.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)

        # 执行查询
        result = await self.db.execute(query)
        collections = result.scalars().unique().all()

        return collections, total

    async def get_collection_by_id(
        self,
        collection_id: str,
    ) -> Optional[IssueCollection]:
        """获取问题集详情"""
        query = (
            select(IssueCollection)
            .options(joinedload(IssueCollection.creator))
            .where(IssueCollection.id == collection_id)
        )
        result = await self.db.execute(query)
        return result.scalars().unique().first()

    async def create_collection(
        self,
        data: IssueCollectionCreate,
        creator_id: str,
    ) -> IssueCollection:
        """创建问题集"""
        collection = IssueCollection(
            title=data.title,
            description=data.description,
            status=data.status or CollectionStatus.PENDING,
            creator_id=creator_id,
            issue_ids=[],
        )
        self.db.add(collection)
        await self.db.commit()
        await self.db.refresh(collection)
        return collection

    async def update_collection(
        self,
        collection_id: str,
        data: IssueCollectionUpdate,
    ) -> Optional[IssueCollection]:
        """更新问题集"""
        query = select(IssueCollection).where(IssueCollection.id == collection_id)
        result = await self.db.execute(query)
        collection = result.scalars().first()

        if not collection:
            return None

        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(collection, key, value)

        collection.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(collection)
        return collection

    async def delete_collection(
        self,
        collection_id: str,
    ) -> bool:
        """删除问题集"""
        query = select(IssueCollection).where(IssueCollection.id == collection_id)
        result = await self.db.execute(query)
        collection = result.scalars().first()

        if not collection:
            return False

        await self.db.delete(collection)
        await self.db.commit()
        return True

    # ========================================================================
    # 统计相关
    # ========================================================================

    async def get_collection_statistics(
        self,
        collection_id: str,
    ) -> Optional[CollectionStatistics]:
        """获取问题集统计信息"""
        # 获取问题集
        collection = await self.get_collection_by_id(collection_id)
        if not collection:
            return None

        issue_ids = collection.issue_ids or []

        # 如果没有关联的 Issue，返回空统计
        if not issue_ids:
            return CollectionStatistics(
                total=0,
                completed=0,
                in_progress=0,
                pending=0,
                completion_rate=0.0,
            )

        # 查询关联的 Issue 状态
        query = select(Issue.status).where(Issue.id.in_(issue_ids))
        result = await self.db.execute(query)
        statuses = [row[0] for row in result.all()]

        # 统计各状态数量
        total = len(statuses)
        completed = sum(1 for s in statuses if s in [IssueStatus.RESOLVED, IssueStatus.CLOSED])
        in_progress = sum(1 for s in statuses if s == IssueStatus.IN_PROGRESS)
        pending = sum(1 for s in statuses if s in [IssueStatus.OPEN, IssueStatus.FEEDBACK])
        completion_rate = completed / total if total > 0 else 0.0

        return CollectionStatistics(
            total=total,
            completed=completed,
            in_progress=in_progress,
            pending=pending,
            completion_rate=completion_rate,
        )

    # ========================================================================
    # 拆解相关
    # ========================================================================

    async def parse_and_create_issues(
        self,
        collection_id: str,
        issues_data: List[Dict[str, Any]],
        creator_id: str,
    ) -> Tuple[List[str], int]:
        """拆解问题集并创建 Issue

        Args:
            collection_id: 问题集 ID
            issues_data: 拆解出的问题数据列表
            creator_id: 创建人 ID

        Returns:
            (创建的 Issue ID 列表, 成功创建的数量)
        """
        from opentask.models.issue.model import Issue
        from opentask.models.issue.enums import IssueType, IssuePriority
        from opentask.models.issue.model import generate_uuid
        import logging

        logger = logging.getLogger(__name__)

        # 使用原始 SQL 查询避免 ORM 的 lazy loading 问题
        from sqlalchemy import text

        query = text("""
            SELECT id, title, description, status, issue_ids, creator_id
            FROM issue_collections
            WHERE id = :collection_id
        """)
        result = await self.db.execute(query, {"collection_id": collection_id})
        row = result.fetchone()

        if not row:
            return [], 0

        # 获取数据（通过列索引或列名）
        collection_id_from_db = row[0]
        collection_title = row[1]
        collection_description = row[2]
        collection_status = row[3]
        collection_issue_ids_raw = row[4] or "[]"
        # 解析 JSON 字符串为列表
        if isinstance(collection_issue_ids_raw, str):
            collection_issue_ids = json.loads(collection_issue_ids_raw)
        else:
            collection_issue_ids = collection_issue_ids_raw
        collection_creator_id = row[5]

        created_issue_ids = []

        print(f"[DEBUG] parse_and_create_issues called with {len(issues_data)} issues")
        print(f"[DEBUG] issues_data: {issues_data}")

        # 获取 IssueService 用于生成 issue_code
        from opentask.services.issue_service import IssueService
        issue_service = IssueService(self.db)

        # 批量创建 Issue
        for issue_data in issues_data:
            try:
                # 获取并转换 type 字符串为 IssueType 枚举
                type_str = issue_data.get("type", "bug")
                try:
                    issue_type = IssueType(type_str)
                except ValueError:
                    logger.warning(f"Invalid issue type '{type_str}', defaulting to 'bug'")
                    issue_type = IssueType.BUG

                # 获取并转换 priority 字符串为 IssuePriority 枚举
                priority_str = issue_data.get("priority", "medium")
                try:
                    issue_priority = IssuePriority(priority_str)
                except ValueError:
                    logger.warning(f"Invalid issue priority '{priority_str}', defaulting to 'medium'")
                    issue_priority = IssuePriority.MEDIUM

                # 生成 issue_code
                issue_code = await issue_service._generate_issue_code()

                # 准备描述
                description = issue_data.get("description", "")
                if collection_title:
                    mention = f"\n\n---\n\n> 来源问题集：@{collection_title}"
                    description += mention

                # 使用原始 SQL 插入 Issue
                # status/is_deleted/created_at/updated_at 均 NOT NULL 且仅有 Python 端默认，
                # 原始 SQL 绕过 ORM，必须显式给值（与模型 insert_default 一致）
                insert_query = text("""
                    INSERT INTO issues (
                        id, title, description, type, priority, status, reporter_id,
                        issue_code, created_by, updated_by, comment_count, attachment_count, view_count,
                        is_deleted, created_at, updated_at
                    ) VALUES (
                        :id, :title, :description, :type, :priority, 'open', :reporter_id,
                        :issue_code, :created_by, :updated_by, 0, 0, 0,
                        FALSE, NOW(), NOW()
                    )
                """)
                new_issue_id = generate_uuid()
                await self.db.execute(insert_query, {
                    "id": new_issue_id,
                    "title": issue_data.get("title", "未命名问题"),
                    "description": description,
                    "type": issue_type.value,
                    "priority": issue_priority.value,
                    "reporter_id": creator_id,
                    "issue_code": issue_code,
                    "created_by": creator_id,
                    "updated_by": creator_id,
                })

                created_issue_ids.append(new_issue_id)
                print(f"[DEBUG] Created issue {new_issue_id}: {issue_data.get('title', '未命名问题')}")

            except Exception as e:
                logger.error(f"Error creating issue: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await self.db.rollback()
                continue

        # 更新问题集的 issue_ids
        updated_issue_ids = collection_issue_ids + created_issue_ids
        update_query = text("""
            UPDATE issue_collections
            SET issue_ids = :issue_ids,
                status = :status,
                updated_at = NOW()
            WHERE id = :collection_id
        """)
        await self.db.execute(update_query, {
            "collection_id": collection_id,
            "issue_ids": json.dumps(updated_issue_ids) if updated_issue_ids else "[]",
            "status": "completed" if created_issue_ids else collection_status
        })

        await self.db.commit()

        return created_issue_ids, len(created_issue_ids)
