"""知识分类 API 路由"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.schemas.knowledge import CategoryResponse
from opentask.services.knowledge.knowledge_category_service import KnowledgeCategoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-categories", tags=["知识分类管理"])


async def get_category_service(
    db: AsyncSession = Depends(get_session)
) -> KnowledgeCategoryService:
    """获取知识分类服务依赖"""
    return KnowledgeCategoryService(db)


class CategoryCreate(BaseModel):
    """创建分类 Schema"""
    name: str = Field(..., description="分类名称")
    icon: Optional[str] = Field(None, description="图标")
    sort_order: int = Field(0, description="排序序号")
    parent_id: Optional[int] = Field(None, description="父分类 ID")


class CategoryUpdate(BaseModel):
    """更新分类 Schema"""
    name: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    parent_id: Optional[int] = None


@router.get("")
async def get_categories(
    parent_id: Optional[int] = Query(None, description="父分类 ID"),
    service: KnowledgeCategoryService = Depends(get_category_service),
):
    """获取分类列表"""
    categories = await service.get_categories(parent_id=parent_id)
    rows = [CategoryResponse.model_validate(c) for c in categories]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": rows,
            "total": len(rows),
        },
        "timestamp": 0,
    }


@router.get("/tree")
async def get_category_tree(
    service: KnowledgeCategoryService = Depends(get_category_service),
):
    """获取分类树"""
    tree = await service.get_category_tree()

    return {
        "code": 200,
        "message": "success",
        "data": tree,
        "timestamp": 0,
    }


@router.get("/{category_id}")
async def get_category(
    category_id: int,
    service: KnowledgeCategoryService = Depends(get_category_service),
):
    """获取分类详情"""
    category = await service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    data = CategoryResponse.model_validate(category)

    return {
        "code": 200,
        "message": "success",
        "data": data,
        "timestamp": 0,
    }


@router.post("")
async def create_category(
    data: CategoryCreate,
    service: KnowledgeCategoryService = Depends(get_category_service),
):
    """创建分类"""
    try:
        category = await service.create_category(
            name=data.name,
            icon=data.icon,
            sort_order=data.sort_order,
            parent_id=data.parent_id,
        )
        response_data = CategoryResponse.model_validate(category)

        return {
            "code": 200,
            "message": "分类创建成功",
            "data": response_data,
            "timestamp": 0,
        }
    except Exception as e:
        logger.error(f"创建分类失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    service: KnowledgeCategoryService = Depends(get_category_service),
):
    """更新分类"""
    category = await service.update_category(
        category_id=category_id,
        name=data.name,
        icon=data.icon,
        sort_order=data.sort_order,
        parent_id=data.parent_id,
    )
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    response_data = CategoryResponse.model_validate(category)

    return {
        "code": 200,
        "message": "分类更新成功",
        "data": response_data,
        "timestamp": 0,
    }


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    service: KnowledgeCategoryService = Depends(get_category_service),
):
    """删除分类"""
    try:
        success = await service.delete_category(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="分类不存在")

        return {
            "code": 200,
            "message": "分类删除成功",
            "data": None,
            "timestamp": 0,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
