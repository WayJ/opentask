"""Dashboard API 路由"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.services.dashboard_service import DashboardService
from opentask.api.dashboard.schemas import DashboardOverviewResponse
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


async def get_dashboard_service(db: AsyncSession = Depends(get_session)) -> DashboardService:
    """获取 Dashboard 服务实例"""
    return DashboardService(db)


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_overview(
    project_id: Optional[str] = Query(None, description="项目 ID 筛选"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    获取研发效能看板总览数据

    包含需求统计、Issue统计、状态分布、类型分布、优先级分布、趋势数据、最近动态
    """
    data = await service.get_overview(project_id)
    return DashboardOverviewResponse(
        code=200,
        message="success",
        data=data,
        timestamp=int(time.time() * 1000),
    )
