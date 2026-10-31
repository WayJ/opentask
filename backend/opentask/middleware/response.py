"""API 响应中间件 - 统一响应格式

符合 API_SPECIFICATION.md 规范：
{
  "code": 200,
  "message": "success",
  "data": { /* 实际数据 */ },
  "timestamp": 1701234567890
}
"""
import time
from typing import Any, Callable
from fastapi import Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from opentask.utils.response import success_response, error_response, StatusCode


class ResponseMiddleware(BaseHTTPMiddleware):
    """统一响应格式中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求响应"""
        try:
            response = await call_next(request)

            # 如果是 JSONResponse 且不包含标准格式，则包装
            if isinstance(response, JSONResponse):
                # 检查响应体是否已经是标准格式
                body = getattr(response, '_body', None)
                if body:
                    import json
                    try:
                        data = json.loads(body)
                        # 如果已经是标准格式（有 code 和 timestamp），直接返回
                        if isinstance(data, dict) and 'code' in data and 'timestamp' in data:
                            return response
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass

                # 否则包装成标准格式
                return JSONResponse(
                    content=success_response(data=response.body if hasattr(response, 'body') else {}),
                    status_code=response.status_code
                )

            return response
        except Exception as e:
            # 处理异常并返回标准错误格式
            return JSONResponse(
                content=error_response(
                    message=str(e),
                    code=StatusCode.INTERNAL_ERROR
                ),
                status_code=500
            )
