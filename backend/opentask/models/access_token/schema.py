"""AccessToken Pydantic Schema"""
from datetime import datetime
from typing import Optional
from pydantic import Field, BaseModel


class AccessTokenCreate(BaseModel):
    """创建 Access Token Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Token 名称")
    description: Optional[str] = Field(None, max_length=1000, description="Token 描述")


class AccessTokenResponse(BaseModel):
    """Access Token 响应 Schema（不含 token 值）"""
    id: str = Field(..., description="Token ID")
    user_id: str = Field(..., description="用户 ID")
    name: str = Field(..., description="Token 名称")
    description: Optional[str] = Field(None, description="Token 描述")
    token_prefix: str = Field(..., description="Token 前缀")
    expires_at: datetime = Field(..., description="过期时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AccessTokenCreateResponse(AccessTokenResponse):
    """创建 Access Token 响应 Schema（包含完整 token，仅返回一次）"""
    token: str = Field(..., description="完整 Token 值（仅创建时返回）")
