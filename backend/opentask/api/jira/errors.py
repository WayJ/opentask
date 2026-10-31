"""Jira 线格式层错误：CONTRACT_* 语义 + Jira 形状错误体

Orca 适配器读错误体的字段为 ``errorMessages[]`` / ``errors{}`` / ``message``
（探测报告 §1，源码 mxt 函数）；本层所有语义错误统一为::

    {"errorMessages": ["CONTRACT_XXX: 可读消息"], "errors": {}}

（字段级错误放 ``errors.{field}``。）错误码沿用 tasks 契约层 CONTRACT_*
命名族（errors.py 常量唯一定义处，直接复用不复制）。
"""

from typing import Dict, Final, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from opentask.api.tasks.errors import (
    AUTH_CODE_INVALID,
    AUTH_CODE_MISSING,
    CODE_FORBIDDEN,
    CODE_STATUS_UNKNOWN,
    CODE_TASK_NOT_FOUND,
    CODE_UNAVAILABLE,
)


class JiraWireError(Exception):
    """Jira 线格式语义错误（HTTP 状态 + CONTRACT_* 错误码 + 可读消息）"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field: Optional[str] = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field

    def to_body(self) -> Dict:
        """Jira 形状错误体（CONTRACT_* 错误码保留在文本前缀）"""
        text = f"{self.code}: {self.message}"
        if self.field:
            return {"errorMessages": [], "errors": {self.field: text}}
        return {"errorMessages": [text], "errors": {}}


def jira_auth_missing(message: str) -> JiraWireError:
    return JiraWireError(401, AUTH_CODE_MISSING, message)


def jira_auth_invalid(message: str) -> JiraWireError:
    return JiraWireError(401, AUTH_CODE_INVALID, message)


def jira_not_found(message: str) -> JiraWireError:
    return JiraWireError(404, CODE_TASK_NOT_FOUND, message)


def jira_unavailable(message: str) -> JiraWireError:
    return JiraWireError(503, CODE_UNAVAILABLE, message)


def jira_bad_request(
    message: str, code: str = "CONTRACT_JQL_INVALID", field: Optional[str] = None
) -> JiraWireError:
    """400（JQL 子集外/请求形状问题；code 可换 CONTRACT_STATUS_UNKNOWN 等）"""
    return JiraWireError(400, code, message, field=field)


def jira_status_unknown(message: str, field: Optional[str] = None) -> JiraWireError:
    return JiraWireError(400, CODE_STATUS_UNKNOWN, message, field=field)


def jira_forbidden(message: str) -> JiraWireError:
    return JiraWireError(403, CODE_FORBIDDEN, message)


async def jira_wire_error_handler(request: Request, exc: JiraWireError) -> JSONResponse:
    """JiraWireError → Jira 形状错误体（401 附 WWW-Authenticate）"""
    headers = (
        {"WWW-Authenticate": "Basic realm=\"OpenTask Jira\", Bearer"}
        if exc.status_code == 401
        else None
    )
    return JSONResponse(
        status_code=exc.status_code, content=exc.to_body(), headers=headers
    )


async def jira_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求结构校验失败 → 400 Jira 形状（Jira 对坏请求体即 400，非 422）"""
    errors: Dict[str, str] = {}
    for item in exc.errors():
        loc = ".".join(str(p) for p in item.get("loc", ()) if p != "body")
        field = loc or "request"
        errors.setdefault(field, item.get("msg", "invalid request"))
    return JSONResponse(
        status_code=400,
        content={
            "errorMessages": ["CONTRACT_REQUEST_INVALID: 请求结构不合法"],
            "errors": errors,
        },
    )


# 禁操作映射：Jira 线格式复用 contract.forbidden_operations 的操作语义
# （get_task/update_task 对应读写；jira 侧无 delete 端点）
FORBIDDEN_OP_BY_ROUTE: Final[Dict[str, str]] = {
    "search": "list_tasks",
    "create": "create_task",
    "get": "get_task",
    "update": "update_task",
    "transition": "update_task",
}
