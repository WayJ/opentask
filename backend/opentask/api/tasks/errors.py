"""契约层统一错误语义（S6 定稿，HC1：沿用 CONTRACT_* 命名族）

错误模型（与路由 schema 一致，见 schemas.ContractErrorResponse）：
所有契约层语义错误响应体均为::

    {"detail": {"code": "<CONTRACT_*>", "message": "<可读消息>"}}

错误码族（HTTP 状态 ↔ 错误码一一对应，可独立辨识）：

=========== ============================== ================================
HTTP        code                           触发场景
=========== ============================== ================================
401         CONTRACT_AUTH_MISSING          未携带 Bearer 凭证
401         CONTRACT_AUTH_INVALID          凭证错误/过期/吊销/用户禁用
400         CONTRACT_AUTH_UNSUPPORTED_GRANT token 端点不支持的 grant_type
403         CONTRACT_FORBIDDEN             操作被配置禁用（禁操作）
404         CONTRACT_TASK_NOT_FOUND        任务不存在（含软删除后）
422         CONTRACT_STATUS_UNKNOWN        状态词表外的状态值（schema 违规）
503         CONTRACT_UNAVAILABLE           后端依赖（数据库）不可达
=========== ============================== ================================

结构性的请求 schema 违规（缺字段/类型错/超长等静态可校验项）仍走
FastAPI 标准 422（HTTPValidationError 形状）；配置依赖的运行时校验
（状态词表）与契约层语义错误统一带 code 字段。

503 语义（S6）：契约层把数据库视为后端依赖，经 get_contract_session
依赖在进入处理逻辑前探测可用性；不可达（连接拒绝/断连）一律
503 CONTRACT_UNAVAILABLE，不裸抛 500。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import DisconnectionError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session

from .schemas import ContractErrorResponse

logger = logging.getLogger(__name__)

# ============================================================================
# 错误码（HC1 命名族；401/400 三项自 S5 迁入，本模块为唯一定义处）
# ============================================================================

AUTH_CODE_MISSING = "CONTRACT_AUTH_MISSING"  # 未携带凭证（401）
AUTH_CODE_INVALID = "CONTRACT_AUTH_INVALID"  # 凭证错误/过期/吊销/用户禁用（401）
AUTH_CODE_UNSUPPORTED_GRANT = "CONTRACT_AUTH_UNSUPPORTED_GRANT"  # token 端点不支持的花式（400）
CODE_FORBIDDEN = "CONTRACT_FORBIDDEN"  # 禁操作（403）
CODE_TASK_NOT_FOUND = "CONTRACT_TASK_NOT_FOUND"  # 任务不存在（404）
CODE_STATUS_UNKNOWN = "CONTRACT_STATUS_UNKNOWN"  # 状态词表外的状态值（422）
CODE_UNAVAILABLE = "CONTRACT_UNAVAILABLE"  # 后端依赖不可达（503）


def contract_error(status_code: int, code: str, message: str) -> HTTPException:
    """构造契约层错误（错误体含可辨识错误码字段；401 附 WWW-Authenticate）"""
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers,
    )


# ============================================================================
# OpenAPI 错误响应声明（routes= 复用；模型即 schemas.ContractErrorResponse）
# ============================================================================


def error_response(
    status_code: int, description: str
) -> Dict[str, Dict[str, Any]]:
    """单个错误状态码的 responses 片段（引用统一错误响应模型）"""
    return {
        str(status_code): {
            "model": ContractErrorResponse,
            "description": description,
        }
    }


ERR_401 = error_response(401, "缺凭证/凭证无效（CONTRACT_AUTH_MISSING / CONTRACT_AUTH_INVALID）")
ERR_400_GRANT = error_response(400, "不支持的 grant_type（CONTRACT_AUTH_UNSUPPORTED_GRANT）")
ERR_403 = error_response(403, "操作被配置禁用（CONTRACT_FORBIDDEN，contract.forbidden_operations）")
ERR_404 = error_response(404, "任务不存在或已软删除（CONTRACT_TASK_NOT_FOUND）")
ERR_503 = error_response(503, "后端依赖（数据库）不可达（CONTRACT_UNAVAILABLE）")

# 422 双形状：结构性违规为 FastAPI 标准校验体；状态词表违规为带 code 的
# CONTRACT_STATUS_UNKNOWN（词表随配置运行时变化，静态 spec 无法穷举，
# 故此处不绑定单一模型，仅描述两种形状）
ERR_422 = {
    "422": {
        "description": "schema 违规：结构性问题返回 FastAPI 标准校验体"
        "（detail=[{loc,msg,type}]）；状态值不在生效词表内返回"
        " detail={code: CONTRACT_STATUS_UNKNOWN, message}"
    }
}


# ============================================================================
# 可用性探测依赖（503 CONTRACT_UNAVAILABLE 唯一来源）
# ============================================================================

# 连接级异常（不包含 IntegrityError 等业务 DBAPIError 子类——那类错误
# 与"依赖不可达"语义无关，仍走各自既有路径）。含 OSError：asyncpg 连接
# 超时（TimeoutError）/拒绝（ConnectionRefusedError）经 SQLAlchemy 异步
# 依赖解析层会以原生 OSError 族穿透（不包成 DBAPIError），实测于
# tests/tasks/test_tasks_errors.py 的死引擎用例。
_CONNECTION_ERRORS = (OperationalError, InterfaceError, DisconnectionError, OSError)


async def get_contract_session(
    session: AsyncSession = Depends(get_session),
) -> AsyncSession:
    """契约层会话依赖：get_session + 依赖可用性探测

    在进入鉴权/业务逻辑前执行一次轻量查询（SELECT 1）：数据库不可达
    （连接拒绝/驱动连接错误/断连）时统一 503 CONTRACT_UNAVAILABLE，
    保证四个契约端点（/tasks CRUD、/tasks/token）的不可达语义一致，
    且优先级高于 401（凭证无法在依赖不可达时验证）。
    会话生命周期仍由底层 get_session 依赖管理。
    """
    try:
        await session.execute(select(1))
    except _CONNECTION_ERRORS as e:
        logger.warning("契约层后端依赖不可达: %s", e)
        raise contract_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            CODE_UNAVAILABLE,
            "后端依赖不可达（数据库连接失败），请稍后重试",
        ) from e
    return session


# re-export：schemas.ContractErrorResponse 供路由声明（避免循环导入说明：
# schemas 不依赖本模块，本模块单向引用 schemas）
__all__ = [
    "AUTH_CODE_MISSING",
    "AUTH_CODE_INVALID",
    "AUTH_CODE_UNSUPPORTED_GRANT",
    "CODE_FORBIDDEN",
    "CODE_TASK_NOT_FOUND",
    "CODE_STATUS_UNKNOWN",
    "CODE_UNAVAILABLE",
    "ContractErrorResponse",
    "contract_error",
    "error_response",
    "ERR_401",
    "ERR_400_GRANT",
    "ERR_403",
    "ERR_404",
    "ERR_422",
    "ERR_503",
    "get_contract_session",
]
