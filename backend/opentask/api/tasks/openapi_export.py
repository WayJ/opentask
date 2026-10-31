"""契约路由 OpenAPI spec 导出（S6 D3：FastAPI 既有机制，随代码提交）

用 FastAPI 的自动生成机制，仅挂载任务源契约路由生成独立 spec
（与全量 openapi.json 分开，避免混淆）：

    cd backend
    AUTH_SECRET_KEY=<密钥> uv run python -m opentask.api.tasks.openapi_export
    # → backend/openapi_contract.json

- 路由/模型/错误响应（401/403/404/503 等，responses= 声明）均由
  FastAPI 从代码推导，无手写 spec（拒绝漂移）；
  一致性由 tests/tasks/test_tasks_openapi.py 的对账测试守护
  （spec 文件与实时生成结果不一致即测试失败）。
- 单独建 app 而非从全量 App 过滤：契约路由在 app.py 挂载时无前缀、
  无附加依赖，单独挂载生成的路径与真实服务完全一致。
"""

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI

from .router import router
from .schemas import CONTRACT_VERSION

# backend/openapi_contract.json（随代码提交的契约 spec）
EXPORT_PATH = Path(__file__).resolve().parents[3] / "openapi_contract.json"

_DESCRIPTION = """\
OpenTask 以「通用任务源」形态对外暴露的任务契约（对接 Orca 等 AI 编排工具，
模拟 Jira 对接模式）。

- 鉴权：`Authorization: Bearer <API Key(vk_) 或 JWT>`；先用
  `POST /tasks/token`（OAuth2 client credentials）以 API Key 换短时效 JWT，
  或直接以 API Key 作 Bearer 凭证。除 `POST /tasks/token` 与
  `GET /capabilities` 外均需凭证。
- 错误体：契约层语义错误统一为 `{"detail": {"code": "CONTRACT_*",
  "message": "..."}}`（401 CONTRACT_AUTH_MISSING/INVALID、403
  CONTRACT_FORBIDDEN、404 CONTRACT_TASK_NOT_FOUND、422
  CONTRACT_STATUS_UNKNOWN、503 CONTRACT_UNAVAILABLE）。
- 能力协商：先调 `GET /capabilities` 获取生效状态词表、分页/游标特性
  与禁操作表，再按能力调用。
- 完整文档见 backend/README.md「任务源契约 API」章节。
"""


def build_contract_openapi() -> Dict[str, Any]:
    """构建契约路由的 OpenAPI spec（仅含契约端点，FastAPI 自动生成）"""
    app = FastAPI(
        title="OpenTask Task Source Contract API",
        version=CONTRACT_VERSION,
        description=_DESCRIPTION,
    )
    app.include_router(router)
    return app.openapi()


def export_contract_openapi() -> Path:
    """生成并写入 backend/openapi_contract.json（随代码提交）"""
    spec = build_contract_openapi()
    EXPORT_PATH.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return EXPORT_PATH


if __name__ == "__main__":
    target = export_contract_openapi()
    print(f"契约 OpenAPI spec 已写入: {target}")
