"""E12-S3: PGE task API must advertise Deprecation header (still 2xx)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_preview_prompt_sends_deprecation_header(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/tasks/preview-prompt",
        json={
            "requirement_title": "de-PGE smoke",
            "requirement_id": "00000000-0000-0000-0000-000000000001",
            "description": "legacy preview",
            "required_skills": [],
        },
    )
    assert resp.status_code == 200, resp.text
    # RFC 8594 style boolean string
    assert resp.headers.get("deprecation", "").lower() in ("true", "1", "yes")


@pytest.mark.asyncio
async def test_openapi_marks_pge_tasks_deprecated():
    from opentask.app import App

    app = App()
    schema = app.openapi()
    paths = schema.get("paths") or {}
    post = (paths.get("/api/tasks") or {}).get("post") or {}
    # FastAPI exposes deprecated flag when route.deprecated=True
    assert post.get("deprecated") is True or "deprecated" in (post.get("description") or "").lower()
