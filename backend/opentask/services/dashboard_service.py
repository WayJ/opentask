"""Dashboard 业务逻辑层"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.requirement.model import Requirement, Event
from opentask.models.issue.model import Issue, IssueStatus
from opentask.api.dashboard.schemas import (
    DashboardOverview,
    StatCard,
    StatusDistribution,
    TypeDistribution,
    PriorityDistribution,
    TrendDataPoint,
    RecentActivityItem,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Dashboard 服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview(self, project_id: Optional[str] = None) -> DashboardOverview:
        """获取看板总览数据"""
        req_stats = await self._get_requirement_stats(project_id)
        issue_stats = await self._get_issue_stats(project_id)
        req_by_status = await self._get_requirement_by_status(project_id)
        req_by_priority = await self._get_requirement_by_priority(project_id)
        issue_by_status = await self._get_issue_by_status(project_id)
        issue_by_type = await self._get_issue_by_type(project_id)
        issue_by_priority = await self._get_issue_by_priority(project_id)
        trend = await self._get_trend(project_id)
        recent = await self._get_recent_activities(project_id)

        return DashboardOverview(
            requirements=req_stats,
            issues=issue_stats,
            requirement_by_status=req_by_status,
            requirement_by_priority=req_by_priority,
            issue_by_status=issue_by_status,
            issue_by_type=issue_by_type,
            issue_by_priority=issue_by_priority,
            trend=trend,
            recent_activities=recent,
        )

    async def _get_requirement_stats(self, project_id: Optional[str] = None) -> StatCard:
        """获取需求统计卡片"""
        query = select(Requirement)
        if project_id:
            query = query.where(Requirement.project_id == project_id)

        total_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(total_q)).scalar() or 0

        open_statuses = ["planning", "generating", "evaluating"]
        in_progress_statuses = ["generating", "evaluating"]
        completed_statuses = ["completed", "closed", "archived"]

        base_q = select(Requirement)
        if project_id:
            base_q = base_q.where(Requirement.project_id == project_id)

        open_q = select(func.count()).select_from(
            base_q.where(Requirement.status.in_(open_statuses)).subquery()
        )
        open_count = (await self.db.execute(open_q)).scalar() or 0

        in_progress_q = select(func.count()).select_from(
            base_q.where(Requirement.status.in_(in_progress_statuses)).subquery()
        )
        in_progress_count = (await self.db.execute(in_progress_q)).scalar() or 0

        completed_q = select(func.count()).select_from(
            base_q.where(Requirement.status.in_(completed_statuses)).subquery()
        )
        completed_count = (await self.db.execute(completed_q)).scalar() or 0

        return StatCard(
            total=total,
            open_count=open_count,
            in_progress_count=in_progress_count,
            completed_count=completed_count,
        )

    async def _get_issue_stats(self, project_id: Optional[str] = None) -> StatCard:
        """获取 Issue 统计卡片"""
        query = select(Issue).where(Issue.is_deleted == False)
        if project_id:
            query = query.where(Issue.project_id == project_id)

        total_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(total_q)).scalar() or 0

        open_count = (
            await self.db.execute(
                select(func.count()).select_from(
                    query.where(Issue.status == "open").subquery()
                )
            )
        ).scalar() or 0

        in_progress_count = (
            await self.db.execute(
                select(func.count()).select_from(
                    query.where(Issue.status == "in_progress").subquery()
                )
            )
        ).scalar() or 0

        closed_statuses = ["resolved", "closed"]
        completed_count = (
            await self.db.execute(
                select(func.count()).select_from(
                    query.where(Issue.status.in_(closed_statuses)).subquery()
                )
            )
        ).scalar() or 0

        return StatCard(
            total=total,
            open_count=open_count,
            in_progress_count=in_progress_count,
            completed_count=completed_count,
        )

    async def _get_requirement_by_status(self, project_id: Optional[str] = None) -> list[StatusDistribution]:
        """需求按状态分布"""
        query = select(Requirement.status, func.count(Requirement.id)).group_by(Requirement.status)
        if project_id:
            query = query.where(Requirement.project_id == project_id)

        result = await self.db.execute(query)
        return [StatusDistribution(status=status, count=count) for status, count in result.all()]

    async def _get_requirement_by_priority(self, project_id: Optional[str] = None) -> list[PriorityDistribution]:
        """需求按优先级分布"""
        query = select(Requirement.priority, func.count(Requirement.id)).group_by(Requirement.priority)
        if project_id:
            query = query.where(Requirement.project_id == project_id)

        result = await self.db.execute(query)
        return [
            PriorityDistribution(priority=priority or "none", count=count)
            for priority, count in result.all()
        ]

    async def _get_issue_by_status(self, project_id: Optional[str] = None) -> list[StatusDistribution]:
        """Issue 按状态分布"""
        query = (
            select(Issue.status, func.count(Issue.id))
            .where(Issue.is_deleted == False)
            .group_by(Issue.status)
        )
        if project_id:
            query = query.where(Issue.project_id == project_id)

        result = await self.db.execute(query)
        return [StatusDistribution(status=status, count=count) for status, count in result.all()]

    async def _get_issue_by_type(self, project_id: Optional[str] = None) -> list[TypeDistribution]:
        """Issue 按类型分布"""
        query = (
            select(Issue.type, func.count(Issue.id))
            .where(Issue.is_deleted == False)
            .group_by(Issue.type)
        )
        if project_id:
            query = query.where(Issue.project_id == project_id)

        result = await self.db.execute(query)
        return [TypeDistribution(type=type_, count=count) for type_, count in result.all()]

    async def _get_issue_by_priority(self, project_id: Optional[str] = None) -> list[PriorityDistribution]:
        """Issue 按优先级分布"""
        query = (
            select(Issue.priority, func.count(Issue.id))
            .where(Issue.is_deleted == False)
            .group_by(Issue.priority)
        )
        if project_id:
            query = query.where(Issue.project_id == project_id)

        result = await self.db.execute(query)
        return [PriorityDistribution(priority=priority, count=count) for priority, count in result.all()]

    async def _get_trend(self, project_id: Optional[str] = None) -> list[TrendDataPoint]:
        """近30天趋势"""
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)

        # 需求创建趋势
        req_query = select(
            func.date(Requirement.created_at).label("date"),
            func.count(Requirement.id).label("count"),
        ).where(Requirement.created_at >= thirty_days_ago)
        if project_id:
            req_query = req_query.where(Requirement.project_id == project_id)
        req_query = req_query.group_by(func.date(Requirement.created_at))
        req_result = await self.db.execute(req_query)
        req_data = {str(row.date): row.count for row in req_result.all()}

        # Issue 创建趋势
        issue_query = select(
            func.date(Issue.created_at).label("date"),
            func.count(Issue.id).label("count"),
        ).where(Issue.created_at >= thirty_days_ago, Issue.is_deleted == False)
        if project_id:
            issue_query = issue_query.where(Issue.project_id == project_id)
        issue_query = issue_query.group_by(func.date(Issue.created_at))
        issue_result = await self.db.execute(issue_query)
        issue_data = {str(row.date): row.count for row in issue_result.all()}

        # 填充完整30天数据
        trend = []
        for i in range(30):
            date = (now - timedelta(days=29 - i)).strftime("%Y-%m-%d")
            trend.append(TrendDataPoint(
                date=date,
                requirement_count=req_data.get(date, 0),
                issue_count=issue_data.get(date, 0),
            ))

        return trend

    async def _get_recent_activities(self, project_id: Optional[str] = None, limit: int = 10) -> list[RecentActivityItem]:
        """获取最近动态（需求和 Issue 混合）"""
        activities = []

        # 最近的需求数据
        req_query = select(Requirement).order_by(Requirement.updated_at.desc()).limit(limit)
        if project_id:
            req_query = req_query.where(Requirement.project_id == project_id)
        req_result = await self.db.execute(req_query)
        for req in req_result.scalars().all():
            activities.append(RecentActivityItem(
                id=req.id,
                type="requirement",
                code=req.code,
                title=req.title,
                status=req.status,
                updated_at=req.updated_at.isoformat() if req.updated_at else "",
            ))

        # 最近的 Issue 数据
        issue_query = (
            select(Issue)
            .where(Issue.is_deleted == False)
            .order_by(Issue.updated_at.desc())
            .limit(limit)
        )
        if project_id:
            issue_query = issue_query.where(Issue.project_id == project_id)
        issue_result = await self.db.execute(issue_query)
        for issue in issue_result.scalars().all():
            activities.append(RecentActivityItem(
                id=issue.id,
                type="issue",
                code=issue.issue_code,
                title=issue.title,
                status=issue.status,
                updated_at=issue.updated_at.isoformat() if issue.updated_at else "",
            ))

        # 按更新时间降序排序，取前 limit 条
        activities.sort(key=lambda x: x.updated_at, reverse=True)
        return activities[:limit]
