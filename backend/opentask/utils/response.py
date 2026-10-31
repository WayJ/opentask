"""统一 API 响应格式工具函数

符合 API_SPECIFICATION.md 规范：
{
  "code": 200,
  "message": "success",
  "data": { /* 实际数据 */ },
  "timestamp": 1701234567890
}
"""
import time
from typing import Any, Optional


def success_response(data: Any = None, message: str = "success", code: int = 200) -> dict:
    """
    生成成功响应

    Args:
        data: 响应数据
        message: 响应消息，默认 "success"
        code: 状态码，默认 200

    Returns:
        符合规范的响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data if data is not None else {},
        "timestamp": int(time.time() * 1000)
    }


def error_response(message: str, code: int = 500, data: Any = None) -> dict:
    """
    生成错误响应

    Args:
        message: 错误消息
        code: 错误码，默认 500
        data: 附加数据

    Returns:
        符合规范的错误响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data if data is not None else {},
        "timestamp": int(time.time() * 1000)
    }


# 常用状态码
class StatusCode:
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_ERROR = 500
