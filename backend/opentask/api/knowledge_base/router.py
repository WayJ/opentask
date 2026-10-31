"""知识库 API 路由"""
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    ProjectAssociateRequest,
)
from opentask.services.knowledge.knowledge_base_service import KnowledgeBaseService
from opentask.services.user_center.rbac_service import RbacService
from opentask.auth import authenticate
from opentask.models.user.model import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库管理"])


async def get_kb_service(
    db: AsyncSession = Depends(get_session)
) -> KnowledgeBaseService:
    """获取知识库服务依赖"""
    return KnowledgeBaseService(db)


@router.get("")
async def get_knowledge_bases(
    current: int = Query(1, description="当前页码"),
    pageSize: int = Query(20, description="每页大小"),
    status: str | None = Query(None, description="状态筛选"),
    keyword: str | None = Query(None, description="搜索关键词"),
    service: KnowledgeBaseService = Depends(get_kb_service),
    current_user: UserModel = Depends(authenticate),
):
    """获取知识库列表（数据范围过滤：仅按部门可见集，ALL 档零过滤）"""
    # 数据范围：ALL → None（零过滤）；SELF → 空集（知识库恒不可见）
    visible_dept_ids = await RbacService(service.db).get_visible_dept_ids(current_user)
    skip = (current - 1) * pageSize
    knowledge_bases, total = await service.get_knowledge_bases(
        skip=skip, limit=pageSize, status=status, keyword=keyword,
        visible_dept_ids=visible_dept_ids,
    )

    # 统计每个知识库的知识数量
    for kb in knowledge_bases:
        kb.knowledge_count = len(kb.knowledge_items)

    rows = [KnowledgeBaseResponse.model_validate(kb) for kb in knowledge_bases]

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


@router.get("/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """获取知识库详情"""
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    kb.knowledge_count = len(kb.knowledge_items)
    data = KnowledgeBaseResponse.model_validate(kb)

    return {
        "code": 200,
        "message": "success",
        "data": data,
        "timestamp": 0,
    }


@router.post("")
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseService = Depends(get_kb_service),
    current_user: UserModel = Depends(authenticate),
):
    """创建知识库"""
    # 部门归属快照：取创建人主部门写入（无归属则保持 NULL）
    dept_id = await RbacService(service.db).get_primary_dept_id(current_user)
    kb = await service.create_knowledge_base(data, dept_id=dept_id)
    response_data = KnowledgeBaseResponse.model_validate(kb)

    return {
        "code": 200,
        "message": "知识库创建成功",
        "data": response_data,
        "timestamp": 0,
    }


@router.put("/{kb_id}")
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """更新知识库"""
    kb = await service.update_knowledge_base(kb_id, data)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    kb.knowledge_count = len(kb.knowledge_items)
    response_data = KnowledgeBaseResponse.model_validate(kb)

    return {
        "code": 200,
        "message": "知识库更新成功",
        "data": response_data,
        "timestamp": 0,
    }


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """删除知识库"""
    success = await service.delete_knowledge_base(kb_id)
    if not success:
        raise HTTPException(status_code=404, detail="知识库不存在")

    return {
        "code": 200,
        "message": "知识库删除成功",
        "data": None,
        "timestamp": 0,
    }


@router.post("/{kb_id}/projects")
async def associate_project(
    kb_id: str,
    data: ProjectAssociateRequest,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """关联项目到知识库"""
    # 验证知识库存在
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    association = await service.associate_project(kb_id, data.project_id)

    return {
        "code": 200,
        "message": "项目关联成功",
        "data": {
            "id": association.id,
            "knowledgeBaseId": association.knowledge_base_id,
            "projectId": association.project_id,
            "createdAt": association.created_at.isoformat(),
        },
        "timestamp": 0,
    }


@router.delete("/{kb_id}/projects/{project_id}")
async def disassociate_project(
    kb_id: str,
    project_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """取消项目关联"""
    success = await service.disassociate_project(kb_id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="关联不存在")

    return {
        "code": 200,
        "message": "取消关联成功",
        "data": None,
        "timestamp": 0,
    }


@router.get("/{kb_id}/projects")
async def get_associated_projects(
    kb_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """获取知识库关联的项目列表"""
    # 验证知识库存在
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    projects = await service.get_associated_projects(kb_id)

    rows = []
    for project in projects:
        rows.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "isActive": project.is_active,
            "createdAt": project.created_at.isoformat(),
        })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": rows,
            "total": len(rows),
        },
        "timestamp": 0,
    }
