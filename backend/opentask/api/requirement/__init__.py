"""需求模块 API"""
from fastapi import APIRouter
from opentask.api.requirement.router import router

__all__ = ["router"]

# 导出的路由器，供主应用注册
requirement_router = router
