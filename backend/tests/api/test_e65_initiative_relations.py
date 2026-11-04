"""E65: Initiative relations mid (blocks / is_blocked_by / relates_to)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.initiative.model import INITIATIVE_RELATION_TYPES, InitiativeRelation


def test_e65_relation_types_q1a():
    assert INITIATIVE_RELATION_TYPES == ("blocks", "is_blocked_by", "relates_to")
    assert InitiativeRelation.__tablename__ == "initiative_relations"


async def _register(client: AsyncClient, prefix: str = "e65"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _ini(client: AsyncClient, h: dict, name: str) -> dict:
    r = await client.post("/api/initiatives", headers=h, json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["data"]
