"""E46：Display conditionalFormats normalize + write cap."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e46c"):
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


def _auth(token: str, workspace_id: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id}


def test_normalize_conditional_formats_unit():
    from opentask.services.display_prefs.service import normalize_display_json

    d = normalize_display_json(
        {
            "conditional_formats": [
                {
                    "id": "c1",
                    "when": {"field": "cf:risk", "op": "gte", "value": 8},
                    "style": {"rowTint": "danger"},
                    "target": "row",
                },
                {
                    "id": "bad",
                    "when": {"field": "cf:x", "op": "bogus", "value": 1},
                    "style": {"rowTint": "danger"},
                    "target": "row",
                },
                {
                    "when": {"field": "priority", "op": "eq", "value": "high"},
                    "style": {"rowTint": "warning"},
                    "target": "cell",
                },
            ]
        }
    )
    assert len(d["conditional_formats"]) == 2
    assert d["conditional_formats"][0]["style"]["rowTint"] == "danger"
    assert d["conditional_formats"][1]["target"] == "cell"


@pytest.mark.asyncio
async def test_prefs_write_conditional_formats_and_cap(test_client: AsyncClient):
    user = await _register(test_client)
    h = _auth(user["token"], user["workspaceId"])
    base = {
        "view_mode": "list",
        "group_by": "none",
        "swimlane_by": "none",
        "hide_empty_lanes": False,
        "fields": {},
        "custom_field_keys": [],
        "conditional_formats": [
            {
                "id": "c1",
                "when": {"field": "priority", "op": "eq", "value": "high"},
                "style": {"rowTint": "warning"},
                "target": "row",
            }
        ],
    }
    resp = await test_client.put("/api/display-prefs/issue", headers=h, json={"display": base})
    assert resp.status_code == 200, resp.text
    got = resp.json()["data"]["display"]
    assert len(got["conditional_formats"]) == 1
    assert got["conditional_formats"][0]["style"]["rowTint"] == "warning"

    too_many = {
        **base,
        "conditional_formats": [
            {
                "id": f"c{i}",
                "when": {"field": "priority", "op": "eq", "value": "high"},
                "style": {"rowTint": "info"},
                "target": "row",
            }
            for i in range(11)
        ],
    }
    bad = await test_client.put(
        "/api/display-prefs/issue", headers=h, json={"display": too_many}
    )
    assert bad.status_code == 400
    assert "conditional_formats_too_many" in str(bad.json())
