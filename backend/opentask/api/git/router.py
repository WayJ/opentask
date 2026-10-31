"""Git API 路由 - Git 仓库操作接口"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.services.git_service import GitService
from opentask.services.file_storage import FileStorageService
from opentask.services.auto_commit_service import AutoCommitService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/git", tags=["Git管理"])


async def get_git_service(
    storage: FileStorageService = Depends(FileStorageService)
) -> GitService:
    """获取 Git 服务依赖"""
    return GitService(storage)


@router.get("/status/{kb_id}")
async def get_git_status(
    kb_id: str,
    service: GitService = Depends(get_git_service)
):
    """获取知识库 Git 状态"""
    status = service.get_status(kb_id)
    if not status.get("is_repo"):
        raise HTTPException(status_code=404, detail="知识库不是 Git 仓库")
    return status


@router.post("/init/{kb_id}")
async def init_git_repo(
    kb_id: str,
    service: GitService = Depends(get_git_service)
):
    """初始化知识库 Git 仓库"""
    try:
        repo = service.init_repo(kb_id)
        return {
            "code": 200,
            "message": "Git 仓库初始化成功",
            "data": {
                "kb_id": kb_id,
                "is_bare": repo.bare,
                "head": repo.head.commit.hexsha if repo.heads else None
            }
        }
    except Exception as e:
        logger.error(f"初始化 Git 仓库失败 {kb_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commit/{kb_id}")
async def commit_changes(
    kb_id: str,
    message: str = Query(..., description="提交消息"),
    author: str = Query("system", description="作者"),
    service: GitService = Depends(get_git_service)
):
    """提交变更到 Git 仓库"""
    commit_hash = service.commit_changes(kb_id, message, author)
    if not commit_hash:
        raise HTTPException(status_code=400, detail="提交失败或没有变更")

    return {
        "code": 200,
        "message": "提交成功",
        "data": {
            "kb_id": kb_id,
            "commit_hash": commit_hash,
            "short_hash": commit_hash[:8]
        }
    }


@router.get("/history/{kb_id}")
async def get_history(
    kb_id: str,
    doc_id: Optional[str] = Query(None, description="文档 ID"),
    limit: int = Query(10, description="返回数量限制", ge=1, le=100),
    service: GitService = Depends(get_git_service)
):
    """获取提交历史"""
    history = service.get_history(kb_id, doc_id, limit)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "kb_id": kb_id,
            "doc_id": doc_id,
            "history": history
        }
    }


@router.get("/diff/{kb_id}/{doc_id}")
async def get_diff(
    kb_id: str,
    doc_id: str,
    commit_hash: Optional[str] = Query(None, description="提交 hash"),
    service: GitService = Depends(get_git_service)
):
    """获取文档 diff"""
    diff = service.get_diff(kb_id, doc_id, commit_hash)
    if not diff:
        raise HTTPException(status_code=404, detail="文档不存在或没有 diff")

    return {
        "code": 200,
        "message": "success",
        "data": diff
    }


@router.get("/branches/{kb_id}")
async def list_branches(
    kb_id: str,
    service: GitService = Depends(get_git_service)
):
    """列出所有分支"""
    branches = service.list_branches(kb_id)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "kb_id": kb_id,
            "branches": branches
        }
    }


@router.post("/branch/{kb_id}")
async def create_branch(
    kb_id: str,
    branch_name: str = Query(..., description="分支名称"),
    start_point: Optional[str] = Query(None, description="起始提交"),
    service: GitService = Depends(get_git_service)
):
    """创建分支"""
    success = service.create_branch(kb_id, branch_name, start_point)
    if not success:
        raise HTTPException(status_code=400, detail="创建分支失败")

    return {
        "code": 200,
        "message": "分支创建成功",
        "data": {
            "kb_id": kb_id,
            "branch_name": branch_name
        }
    }


@router.post("/auto-commit/start")
async def start_auto_commit(
    interval: int = Query(300, description="提交间隔（秒）", ge=60, le=3600),
    db: AsyncSession = Depends(get_session),
    storage: FileStorageService = Depends(FileStorageService)
):
    """启动自动提交服务（后台任务）"""
    # TODO: 实现后台任务管理
    # 目前只返回配置信息
    return {
        "code": 200,
        "message": "自动提交服务配置",
        "data": {
            "interval": interval,
            "status": "configured"
        }
    }


@router.post("/auto-commit/stop")
async def stop_auto_commit():
    """停止自动提交服务"""
    # TODO: 实现后台任务管理
    return {
        "code": 200,
        "message": "自动提交服务已停止"
    }
