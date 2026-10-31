"""
通用响应模型
"""
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field
import time


T = TypeVar('T')


class SuccessResponse(BaseModel, Generic[T]):
    """成功响应模型"""
    data: Optional[T] = Field(None, description="响应数据")
    message: str = Field("success", description="响应消息")
    code: int = Field(200, description="状态码")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="时间戳")


class SuccessListResponse(BaseModel, Generic[T]):
    """成功列表响应模型"""
    data: list[T] = Field(default_factory=list, description="响应数据列表")
    message: str = Field("success", description="响应消息")
    code: int = Field(200, description="状态码")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="时间戳")
