"""Git API 模块"""
from fastapi import APIRouter

from .router import router as git_router

__all__ = ["git_router"]
