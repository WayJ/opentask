"""Jira 线格式契约文档对账测试（TD8：契约文档不得与实现漂移）

背景：Jira 线格式层以 ASGI catch-all 挂载（`/rest/api/2/{jira_path:path}`），
FastAPI 不建模，故它**不出现在任何 OpenAPI spec** 里——形状契约的唯一权威是
仓内文档 `backend/docs/jira-wire.md`。没有这道对账，新增端点而忘更文档，
外部适配方就会拿到过期契约。

本测试断言：内层 Jira 路由的每个 (method, path) 都在文档 §4 端点表中出现，
且文档里不残留已删除的端点（双向对账）。
"""

from pathlib import Path

from opentask.api.jira.router import router

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "jira-wire.md"

# 文档表格中会被解析为端点行的 method 集合（大小写归一）
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _implemented_routes() -> set[tuple[str, str]]:
    """内层 Jira 路由的 (method, path) 集合"""
    routes: set[tuple[str, str]] = set()
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method.upper() in _METHODS:
                routes.add((method.upper(), route.path))
    return routes


def _documented_routes() -> set[tuple[str, str]]:
    """文档 §4 端点表中的 (method, path) 集合"""
    assert DOC_PATH.exists(), f"Jira 线格式契约文档缺失：{DOC_PATH}"
    text = DOC_PATH.read_text(encoding="utf-8")
    rows: set[tuple[str, str]] = set()
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        method = cells[0].upper()
        if method not in _METHODS:
            continue
        path = cells[1].strip("`").strip()
        if not path.startswith("/"):
            continue
        rows.add((method, path))
    return rows


def test_doc_file_exists():
    """契约文档必须存在于仓内（TD8 的还款条件）"""
    assert DOC_PATH.exists(), (
        f"缺少 Jira 线格式契约文档：{DOC_PATH}；"
        "该层不进 OpenAPI spec，文档是外部适配方的唯一权威"
    )


def test_every_implemented_route_is_documented():
    """已实现的每个端点都必须在文档端点表中出现"""
    implemented = _implemented_routes()
    documented = _documented_routes()
    missing = sorted(implemented - documented)
    assert not missing, (
        f"Jira 线端点已实现但未写入 {DOC_PATH.name}：{missing}；"
        "新增端点后必须同步更新契约文档（§4 端点表）"
    )


def test_documented_routes_are_not_stale():
    """文档中不得残留已删除的端点（反向对账，防文档腐化）"""
    implemented = _implemented_routes()
    documented = _documented_routes()
    stale = sorted(documented - implemented)
    assert not stale, (
        f"{DOC_PATH.name} 中存在已不存在的端点：{stale}；"
        "删除端点后必须同步清理契约文档"
    )


def test_doc_declares_key_contract_anchors():
    """文档须声明挂载前缀、鉴权形态与 Jira 形状错误体（三方适配的关键锚点）"""
    text = DOC_PATH.read_text(encoding="utf-8")
    for anchor in ("/rest/api/2", "Authorization: Basic", "Authorization: Bearer", "errorMessages"):
        assert anchor in text, f"{DOC_PATH.name} 缺少关键契约锚点：{anchor}"
