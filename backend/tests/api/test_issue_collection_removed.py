"""问题集专属 API 已移除。表和历史迁移不在本测试里删除。"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from opentask.api.issue.router import router as issue_router
from opentask.api.saved_views.router import router as saved_views_router


def _paths(router) -> set[str]:
    return {getattr(route, "path", "") for route in router.routes}


def test_collection_routes_are_not_registered():
    paths = _paths(issue_router)
    assert not any("collection" in path for path in paths)
    assert "/api/issues/{issue_id}" in paths or any(path.endswith("/{issue_id}") for path in paths)


def test_openapi_omits_collection_paths():
    app = FastAPI()
    app.include_router(issue_router)
    dumped = json.dumps(app.openapi())
    assert "/api/issues/collections" not in dumped
    assert "IssueCollection" not in dumped


def test_saved_views_router_still_registered():
    paths = _paths(saved_views_router)
    assert any(path.startswith("/api/saved-views") for path in paths)


def test_issue_collection_module_is_not_imported():
    import opentask.api.issue.router as issue_api
    import opentask.models as models

    assert not hasattr(issue_api, "IssueCollectionService")
    assert "IssueCollection" not in getattr(models, "__all__", [])


@pytest.mark.asyncio
async def test_collection_url_is_not_a_collection_resource(test_client: AsyncClient):
    """未登录访问已删除的集合路径：不能返回集合列表。

    路由表里没有 /collections 之后，请求会落到 ``/{issue_id}``。
    未登录时期望 401；已登录且没有这张 Issue 时期望 404。
    """
    anon = await test_client.get("/api/issues/collections")
    assert anon.status_code in {401, 403}
    assert anon.status_code != 200

    uname = f"colrm_{uuid.uuid4().hex[:8]}"
    registered = await test_client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": "Col"},
    )
    assert registered.status_code == 200, registered.text
    token = registered.json()["data"]["token"]
    workspace_id = registered.json()["data"]["defaultWorkspaceId"]
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id}

    missing = await test_client.get("/api/issues/collections", headers=headers)
    assert missing.status_code == 404

    listing = await test_client.get("/api/issues", headers=headers)
    assert listing.status_code == 200

    saved = await test_client.get("/api/saved-views", headers=headers)
    assert saved.status_code == 200

    missing_header = await test_client.get(
        "/api/saved-views",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing_header.status_code == 400
