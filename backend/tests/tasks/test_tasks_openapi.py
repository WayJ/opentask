"""契约 OpenAPI spec 对账测试（S6 S1：spec 随代码提交且与实现一致）

守护两条线：
1. 随代码提交的 backend/openapi_contract.json 与按当前代码实时构建的结果
   完全一致——改路由/schema/错误响应后忘重新导出即失败（拒绝 spec 漂移）；
2. spec 形状对账：覆盖四个契约端点、错误响应模型（ContractErrorResponse）、
   安全方案（HTTPBearer）、以及各模型字段与 pydantic model_fields 一致；
   单独导出 app 与真实 App() 挂载的契约路径一致。
"""

import json

import pytest

from opentask.api.tasks.openapi_export import EXPORT_PATH, build_contract_openapi
from opentask.api.tasks.schemas import (
    CONTRACT_VERSION,
    ContractCapabilities,
    ContractErrorDetail,
    ContractErrorResponse,
    ContractTask,
    ContractTaskListResponse,
    TaskCreate,
    TaskUpdate,
)

CONTRACT_PATHS = {"/tasks", "/tasks/{task_id}", "/tasks/token", "/capabilities"}

# 受保护端点（需 Bearer 凭证；method, path）
PROTECTED_OPERATIONS = [
    ("get", "/tasks"),
    ("post", "/tasks"),
    ("get", "/tasks/{task_id}"),
    ("patch", "/tasks/{task_id}"),
    ("delete", "/tasks/{task_id}"),
]


def test_spec_file_committed_and_in_sync():
    """spec 文件已随代码提交，且与实时构建结果逐字节一致（防漂移）"""
    assert EXPORT_PATH.exists() and EXPORT_PATH.is_file(), (
        f"契约 spec 未随代码提交：{EXPORT_PATH} 不存在，"
        "先运行 uv run python -m opentask.api.tasks.openapi_export"
    )
    checked_in = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    assert checked_in == build_contract_openapi(), (
        "openapi_contract.json 与当前代码不一致：路由/schema/错误响应变更后"
        "需重新运行 python -m opentask.api.tasks.openapi_export 并随代码提交"
    )


def test_spec_covers_exactly_the_contract_routes():
    spec = build_contract_openapi()
    assert set(spec["paths"]) == CONTRACT_PATHS
    assert spec["info"]["title"] == "OpenTask Task Source Contract API"
    assert spec["info"]["version"] == CONTRACT_VERSION


def test_protected_operations_declare_security_and_error_models():
    spec = build_contract_openapi()
    for method, path in PROTECTED_OPERATIONS:
        op = spec["paths"][path][method]
        assert op.get("security"), f"{method.upper()} {path} 应要求 Bearer 凭证"
        for code in ("401", "403", "503"):
            resp = op["responses"][code]
            schema = resp["content"]["application/json"]["schema"]
            assert schema["$ref"] == "#/components/schemas/ContractErrorResponse", (
                f"{method.upper()} {path} {code} 未声明统一错误响应模型"
            )


def test_public_endpoints_declared_public():
    spec = build_contract_openapi()
    assert not spec["paths"]["/tasks/token"]["post"].get("security")
    assert not spec["paths"]["/capabilities"]["get"].get("security")


def test_bearer_security_scheme_declared():
    spec = build_contract_openapi()
    assert "HTTPBearer" in spec["components"]["securitySchemes"]


# ============================================================================
# 字段对账：spec components 中的模型字段 == pydantic model_fields
# ============================================================================

MODELS_UNDER_TEST = [
    ("ContractTask", ContractTask),
    ("ContractTaskListResponse", ContractTaskListResponse),
    ("ContractCapabilities", ContractCapabilities),
    ("TaskCreate", TaskCreate),
    ("TaskUpdate", TaskUpdate),
    ("ContractErrorResponse", ContractErrorResponse),
    ("ContractErrorDetail", ContractErrorDetail),
]


@pytest.mark.parametrize(("spec_name", "model"), MODELS_UNDER_TEST)
def test_spec_model_fields_match_pydantic(spec_name: str, model: type):
    """spec 中各模型属性集与 pydantic 字段集逐一相等（含错误响应模型）"""
    spec = build_contract_openapi()
    props = spec["components"]["schemas"][spec_name]["properties"]
    assert set(props) == set(model.model_fields), (
        f"{spec_name}: spec 字段 {sorted(props)} 与 pydantic 字段 "
        f"{sorted(model.model_fields)} 不一致"
    )


def test_export_matches_real_app_contract_mount_paths():
    """单独导出的 spec 与真实 App() 挂载的契约路径一致（挂根、无前缀）"""
    from opentask.app import App

    app = App()
    real_paths = {
        route.path
        for route in app.routes
        if route.path.startswith("/tasks") or route.path == "/capabilities"
    }
    assert real_paths == CONTRACT_PATHS
