"""Access Token 管理 API 路由"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.access_token.schema import (
    AccessTokenCreate,
    AccessTokenResponse,
    AccessTokenCreateResponse,
)
from opentask.services.access_token.service import AccessTokenService
from opentask.repositories.base import get_session
from opentask.utils.response import success_response
from opentask.auth import authenticate
from opentask.models.user.model import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/access-tokens", tags=["Access Tokens"])


async def get_access_token_service(
    db: AsyncSession = Depends(get_session)
) -> AccessTokenService:
    """获取 Access Token 服务依赖"""
    return AccessTokenService(db)


@router.post("")
async def create_access_token(
    dto: AccessTokenCreate,
    current_user: UserModel = Depends(authenticate),
    service: AccessTokenService = Depends(get_access_token_service),
):
    """
    创建 Access Token

    - **name**: Token 名称（必填）
    - **description**: Token 描述（可选）

    返回包含完整 token 的响应，token 仅在创建时显示一次。
    """
    try:
        token, raw_token = await service.create(str(current_user.id), dto)
        return success_response(
            data=service.to_create_response(token, raw_token),
            message="Access Token 创建成功"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_access_tokens(
    current_user: UserModel = Depends(authenticate),
    service: AccessTokenService = Depends(get_access_token_service),
):
    """
    获取当前用户的所有 Access Token

    返回 Token 列表，按创建时间倒序排列。不包含完整 token 值。
    """
    tokens = await service.get_list(str(current_user.id))
    return success_response(
        data=[service.to_response(t) for t in tokens],
        message="获取成功"
    )


@router.delete("/{token_id}")
async def delete_access_token(
    token_id: str,
    current_user: UserModel = Depends(authenticate),
    service: AccessTokenService = Depends(get_access_token_service),
):
    """
    删除 Access Token

    - **token_id**: Token ID
    """
    await service.delete(token_id, str(current_user.id))
    return success_response(message="Access Token 已删除")
