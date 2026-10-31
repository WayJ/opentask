"""知识文档 API 路由"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.schemas.knowledge import (
    KnowledgeCreate,
    KnowledgeUpdate,
    KnowledgeResponse,
)
from opentask.services.knowledge.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["知识文档管理"])


async def get_knowledge_service(
    db: AsyncSession = Depends(get_session)
) -> KnowledgeService:
    """获取知识文档服务依赖"""
    return KnowledgeService(db)


@router.get("")
async def get_knowledges(
    knowledge_base_id: Optional[str] = Query(None, description="知识库 ID"),
    category_id: Optional[int] = Query(None, description="分类 ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    current: int = Query(1, description="当前页码"),
    pageSize: int = Query(20, description="每页大小"),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """获取知识文档列表"""
    skip = (current - 1) * pageSize
    knowledges, total = await service.get_knowledges(
        knowledge_base_id=knowledge_base_id,
        category_id=category_id,
        status=status,
        keyword=keyword,
        skip=skip,
        limit=pageSize,
    )

    rows = [KnowledgeResponse.model_validate(kb) for kb in knowledges]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": rows,
            "total": total,
            "current": current,
            "pageSize": pageSize,
            "totalPages": (total + pageSize - 1) // pageSize,
        },
        "timestamp": 0,
    }


@router.get("/{knowledge_id}")
async def get_knowledge(
    knowledge_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """获取知识文档详情"""
    knowledge = await service.get_knowledge(knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识文档不存在")

    # 增加浏览次数
    await service.increment_view_count(knowledge_id)

    data = KnowledgeResponse.model_validate(knowledge)

    return {
        "code": 200,
        "message": "success",
        "data": data,
        "timestamp": 0,
    }


@router.get("/slug/{slug}")
async def get_knowledge_by_slug(
    slug: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """通过 slug 获取知识文档"""
    knowledge = await service.get_knowledge_by_slug(slug)
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识文档不存在")

    # 增加浏览次数
    await service.increment_view_count(knowledge.id)

    data = KnowledgeResponse.model_validate(knowledge)

    return {
        "code": 200,
        "message": "success",
        "data": data,
        "timestamp": 0,
    }


@router.post("")
async def create_knowledge(
    data: KnowledgeCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """创建知识文档"""
    try:
        knowledge = await service.create_knowledge(data)
        response_data = KnowledgeResponse.model_validate(knowledge)

        return {
            "code": 200,
            "message": "知识文档创建成功",
            "data": response_data,
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"创建知识文档失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{knowledge_id}")
async def update_knowledge(
    knowledge_id: str,
    data: KnowledgeUpdate,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """更新知识文档"""
    knowledge = await service.update_knowledge(knowledge_id, data)
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识文档不存在")

    response_data = KnowledgeResponse.model_validate(knowledge)

    return {
        "code": 200,
        "message": "知识文档更新成功",
        "data": response_data,
        "timestamp": 0,
    }


@router.delete("/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """删除知识文档"""
    success = await service.delete_knowledge(knowledge_id)
    if not success:
        raise HTTPException(status_code=404, detail="知识文档不存在")

    return {
        "code": 200,
        "message": "知识文档删除成功",
        "data": None,
        "timestamp": 0,
    }


@router.post("/{knowledge_id}/like")
async def like_knowledge(
    knowledge_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """点赞知识文档"""
    success = await service.increment_like_count(knowledge_id)
    if not success:
        raise HTTPException(status_code=404, detail="知识文档不存在")

    return {
        "code": 200,
        "message": "点赞成功",
        "data": None,
        "timestamp": 0,
    }


# ============================================================================
# Git 编辑相关端点
# ============================================================================

from opentask.services.git_knowledge_service import GitKnowledgeService


async def get_git_service() -> GitKnowledgeService:
    """获取 Git 服务实例"""
    return GitKnowledgeService()


class CommitRequest(BaseModel):
    """提交请求模型"""
    content: str
    message: str
    author: str = "admin"


class CreateBranchRequest(BaseModel):
    """创建分支请求模型"""
    branch_name: str
    from_branch: str = "main"


class CreatePRRequest(BaseModel):
    """创建 PR 请求模型"""
    title: str
    source_branch: str
    target_branch: str = "main"
    description: Optional[str] = None


@router.get("/kb/{kb_id}/documents/{doc_id}/raw")
async def get_raw_content(
    kb_id: str,
    doc_id: str,
    git_service: GitKnowledgeService = Depends(get_git_service),
):
    """
    获取文档原始 Markdown 内容

    直接从 Git 仓库读取，返回纯文本
    """
    file_path = f"{doc_id}/index.md"

    try:
        content = await git_service.read_file(kb_id, file_path)
        return Response(content=content, media_type="text/markdown; charset=utf-8")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/kb/{kb_id}/documents/{doc_id}/commit")
async def commit_document(
    kb_id: str,
    doc_id: str,
    request: CommitRequest,
    git_service: GitKnowledgeService = Depends(get_git_service),
):
    """
    提交文档到 Git 仓库

    - 更新 Git 仓库
    - 自动同步到数据库
    - 返回 commit SHA
    """
    file_path = f"{doc_id}/index.md"

    try:
        result = await git_service.commit_file(
            kb_id=kb_id,
            file_path=file_path,
            content=request.content,
            message=request.message,
            author=request.author
        )

        return {
            "code": 200,
            "message": "提交成功",
            "data": result,
            "timestamp": 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


@router.get("/kb/{kb_id}/documents/{doc_id}/history")
async def get_document_history(
    kb_id: str,
    doc_id: str,
    limit: int = Query(10, ge=1, le=100, description="返回记录数量"),
    git_service: GitKnowledgeService = Depends(get_git_service),
):
    """获取文档历史记录"""
    file_path = f"{doc_id}/index.md"

    try:
        history = await git_service.get_history(
            kb_id=kb_id,
            file_path=file_path,
            limit=limit
        )

        return {
            "code": 200,
            "message": "success",
            "data": history,
            "timestamp": 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.get("/kb/{kb_id}/documents/{doc_id}/diff")
async def get_document_diff(
    kb_id: str,
    doc_id: str,
    commit_a: Optional[str] = Query(None, description="旧版本 SHA"),
    commit_b: Optional[str] = Query(None, description="新版本 SHA"),
    git_service: GitKnowledgeService = Depends(get_git_service),
):
    """获取文档 diff"""
    file_path = f"{doc_id}/index.md"

    try:
        diff = await git_service.get_diff(
            kb_id=kb_id,
            file_path=file_path,
            commit_a=commit_a,
            commit_b=commit_b
        )

        return {
            "code": 200,
            "message": "success",
            "data": diff,
            "timestamp": 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取 diff 失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取 diff 失败: {str(e)}")


@router.get("/kb/{kb_id}/status")
async def get_knowledge_base_status(
    kb_id: str,
    git_service: GitKnowledgeService = Depends(get_git_service),
):
    """获取知识库 Git 状态"""
    try:
        status = await git_service.get_status(kb_id)

        return {
            "code": 200,
            "message": "success",
            "data": status,
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/kb/{kb_id}/branches")
async def create_branch(
    kb_id: str,
    request: CreateBranchRequest,
    git_service: GitKnowledgeService = Depends(get_git_service),
):
    """创建新分支"""
    try:
        result = await git_service.create_branch(
            kb_id=kb_id,
            branch_name=request.branch_name,
            from_branch=request.from_branch
        )

        return {
            "code": 200,
            "message": "分支创建成功",
            "data": result,
            "timestamp": 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建分支失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建分支失败: {str(e)}")


@router.post("/kb/{kb_id}/pull-requests")
async def create_pull_request(
    kb_id: str,
    request: CreatePRRequest,
    git_service: GitKnowledgeService = Depends(get_git_service),
):
    """
    创建 Pull Request

    注意：此功能需要集成 GitLab/GitHub API，当前为占位实现
    """
    try:
        result = await git_service.create_pull_request(
            kb_id=kb_id,
            title=request.title,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
            description=request.description
        )

        return {
            "code": 200,
            "message": "PR 创建成功" if result.get("status") == "success" else "PR 创建功能待实现",
            "data": result,
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"创建 PR 失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建 PR 失败: {str(e)}")
