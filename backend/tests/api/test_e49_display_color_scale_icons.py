"""E49：Display colorScales + iconSets normalize / caps / no-emit."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e49d"):
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


def test_normalize_color_scales_and_icon_sets_unit():
    from opentask.services.display_prefs.service import normalize_display_json

    d = normalize_display_json(
        {
            "colorScales": [
                {
                    "id": "cs1",
                    "field": "cf:score",
                    "domain": {"min": 0, "max": 10},
                    "palette": "blue_red",
                    "target": "row",
                },
                {
                    "id": "bad",
                    "field": "priority",
                    "domain": {"min": 0, "max": 1},
                    "palette": "blue_red",
                    "target": "row",
                },
                {
                    "id": "badp",
                    "field": "cf:x",
                    "domain": {"min": 0, "max": 1},
                    "palette": "neon",
                    "target": "row",
                },
                {
                    "id": "cs2",
                    "field": "due_date",
                    "domain": {"min": "2020-01-01", "max": "2030-01-01"},
                    "palette": "mono",
                    "target": "cell",
                },
            ],
            "iconSets": [
                {
                    "id": "is1",
                    "field": "cf:risk",
                    "rules": [
                        {"op": "gte", "value": 8, "icon": "arrow_up"},
                        {"op": "lt", "value": 3, "icon": "url_http"},
                        {"op": "bogus", "value": 1, "icon": "flag"},
                    ],
                },
            ],
            "conditional_formats": [
                {
                    "id": "c1",
                    "when": {"field": "priority", "op": "eq", "value": "high"},
                    "style": {"rowTint": "danger"},
                    "target": "row",
                }
            ],
        }
    )
    assert len(d["color_scales"]) == 2
    assert d["color_scales"][0]["palette"] == "blue_red"
    assert d["color_scales"][0]["domain"]["min"] == 0.0
    assert d["color_scales"][0]["domain"]["max"] == 10.0
    assert d["color_scales"][1]["field"] == "due_date"
    assert d["color_scales"][1]["target"] == "cell"
    assert len(d["icon_sets"]) == 1
    assert len(d["icon_sets"][0]["rules"]) == 1
    assert d["icon_sets"][0]["rules"][0]["icon"] == "arrow_up"
    assert len(d["conditional_formats"]) == 1


def test_normalize_scales_cap_truncate_on_read():
    from opentask.services.display_prefs.service import normalize_display_json

    scales = [
        {
            "id": f"cs{i}",
            "field": "estimate_points",
            "domain": {"min": 0, "max": 10},
            "palette": "green_red",
            "target": "row",
        }
        for i in range(7)
    ]
    d = normalize_display_json({"color_scales": scales})
    assert len(d["color_scales"]) == 5


@pytest.mark.asyncio
async def test_prefs_write_scales_icons_and_caps(test_client: AsyncClient):
    user = await _register(test_client)
    h = _auth(user["token"], user["workspaceId"])
    base = {
        "view_mode": "list",
        "group_by": "none",
        "swimlane_by": "none",
        "hide_empty_lanes": False,
        "fields": {},
        "custom_field_keys": [],
        "conditional_formats": [],
        "color_scales": [
            {
                "id": "cs1",
                "field": "cf:score",
                "domain": {"min": 0, "max": 100},
                "palette": "blue_red",
                "target": "row",
            }
        ],
        "icon_sets": [
            {
                "id": "is1",
                "field": "priority",
                "rules": [{"op": "eq", "value": "high", "icon": "flag"}],
            }
        ],
    }
    resp = await test_client.put(
        "/api/display-prefs/issue", headers=h, json={"display": base}
    )
    assert resp.status_code == 200, resp.text
    got = resp.json()["data"]["display"]
    assert len(got["color_scales"]) == 1
    assert got["color_scales"][0]["palette"] == "blue_red"
    assert len(got["icon_sets"]) == 1
    assert got["icon_sets"][0]["rules"][0]["icon"] == "flag"

    too_many_scales = {
        **base,
        "color_scales": [
            {
                "id": f"cs{i}",
                "field": "estimate_points",
                "domain": {"min": 0, "max": 5},
                "palette": "mono",
                "target": "row",
            }
            for i in range(6)
        ],
    }
    bad = await test_client.put(
        "/api/display-prefs/issue", headers=h, json={"display": too_many_scales}
    )
    assert bad.status_code == 400
    assert "color_scales_too_many" in str(bad.json())

    too_many_icons = {
        **base,
        "icon_sets": [
            {
                "id": f"is{i}",
                "field": "priority",
                "rules": [{"op": "eq", "value": "high", "icon": "check"}],
            }
            for i in range(6)
        ],
    }
    bad2 = await test_client.put(
        "/api/display-prefs/issue", headers=h, json={"display": too_many_icons}
    )
    assert bad2.status_code == 400
    assert "icon_sets_too_many" in str(bad2.json())


@pytest.mark.asyncio
async def test_display_prefs_write_no_webhook_automation(test_client: AsyncClient):
    user = await _register(test_client, prefix="e49spy")
    h = _auth(user["token"], user["workspaceId"])
    payload = {
        "view_mode": "list",
        "group_by": "none",
        "swimlane_by": "none",
        "hide_empty_lanes": False,
        "fields": {},
        "custom_field_keys": [],
        "colorScales": [
            {
                "id": "cs1",
                "field": "estimate_points",
                "domain": {"min": 1, "max": 8},
                "palette": "yellow_blue",
                "target": "row",
            }
        ],
        "iconSets": [
            {
                "id": "is1",
                "field": "estimate_points",
                "rules": [{"op": "gte", "value": 5, "icon": "arrow_up"}],
            }
        ],
    }
    with (
        patch(
            "opentask.services.workspace_webhook.service.fire_webhooks",
            new_callable=AsyncMock,
        ) as wh,
        patch(
            "opentask.services.automation.service.fire_automations",
            new_callable=AsyncMock,
        ) as auto,
    ):
        resp = await test_client.put(
            "/api/display-prefs/issue", headers=h, json={"display": payload}
        )
        assert resp.status_code == 200, resp.text
        got = await test_client.get("/api/display-prefs/issue", headers=h)
        assert got.status_code == 200
        assert len(got.json()["data"]["display"]["color_scales"]) == 1
        assert len(got.json()["data"]["display"]["icon_sets"]) == 1
        wh.assert_not_called()
        auto.assert_not_called()
