"""项目模块 API"""
from fastapi import APIRouter
from opentask.api.project.router import router

__all__ = ["router"]

# 导出的路由器，供主应用注册
project_router = router
