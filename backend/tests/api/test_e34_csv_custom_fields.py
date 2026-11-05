"""E34：CSV export/import 含 cf.<key> 自定义字段列。"""
from __future__ import annotations

import csv
import io
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e34"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "username": uname,
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _create_issue(client: AsyncClient, user: dict, title: str) -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": title,
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_cf_helpers_unit():
    from opentask.services.issue_csv.service import (
        format_cf_csv_value,
        parse_cf_header,
        parse_cf_csv_value,
    )
    from opentask.models.custom_field.model import CustomField

    assert parse_cf_header("cf.severity") == "severity"
    assert parse_cf_header("CF.env") == "env"
    assert parse_cf_header("title") is None
    assert parse_cf_header("cf.") is None

    assert format_cf_csv_value(True, "boolean") == "true"
    assert format_cf_csv_value(["a", "b"], "multi_select") == "a,b"
    assert format_cf_csv_value(None, "text") == ""

    field = CustomField(
        id="x",
        workspace_id="w",
        name="Stack",
        key="stack",
        type="multi_select",
        options_json=[{"value": "fe", "label": "FE"}, {"value": "be", "label": "BE"}],
        position=0,
    )
    assert parse_cf_csv_value(field, "fe, be") == ["fe", "be"]
    bool_f = CustomField(
        id="y",
        workspace_id="w",
        name="Shipped",
        key="shipped",
        type="boolean",
        options_json=[],
        position=1,
    )
    assert parse_cf_csv_value(bool_f, "TRUE") is True
    with pytest.raises(ValueError):
        parse_cf_csv_value(bool_f, "yes")


@pytest.mark.asyncio
async def test_export_and_template_include_cf_columns(test_client: AsyncClient):
    user = await _register(test_client, "e34ex")
    h = _auth(user["token"], user["workspaceId"])

    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Severity",
            "key": "severity",
            "type": "single_select",
            "options": [{"value": "s1", "label": "S1"}, {"value": "s2", "label": "S2"}],
        },
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Shipped", "key": "shipped", "type": "boolean"},
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Stack",
            "key": "stack",
            "type": "multi_select",
            "options": [{"value": "fe", "label": "FE"}, {"value": "be", "label": "BE"}],
        },
    )

    issue = await _create_issue(test_client, user, "CF Export Me")
    assert (
        await test_client.patch(
            f"/api/issues/{issue['id']}/custom-fields",
            headers=h,
            json={
                "values": [
                    {"key": "severity", "value": "s1"},
                    {"key": "shipped", "value": True},
                    {"key": "stack", "value": ["fe", "be"]},
                ]
            },
        )
    ).status_code == 200

    tmpl = await test_client.get("/api/issues/import/template.csv", headers=h)
    assert tmpl.status_code == 200, tmpl.text
    assert "cf.severity" in tmpl.text
    assert "cf.shipped" in tmpl.text
    assert "cf.stack" in tmpl.text

    resp = await test_client.get("/api/issues/export.csv", headers=h)
    assert resp.status_code == 200, resp.text
    reader = csv.DictReader(io.StringIO(resp.text))
    assert reader.fieldnames is not None
    for col in ("cf.severity", "cf.shipped", "cf.stack"):
        assert col in reader.fieldnames
    # stable order: after fixed columns
    assert reader.fieldnames.index("updated_at") < reader.fieldnames.index("cf.severity")
    rows = list(reader)
    hit = next(r for r in rows if r["title"] == "CF Export Me")
    assert hit["cf.severity"] == "s1"
    assert hit["cf.shipped"] == "true"
    assert hit["cf.stack"] == "fe,be"


@pytest.mark.asyncio
async def test_import_cf_values_and_unknown_key_partial(test_client: AsyncClient):
    user = await _register(test_client, "e34im")
    h = _auth(user["token"], user["workspaceId"])

    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Severity",
            "key": "severity",
            "type": "single_select",
            "options": [{"value": "s1", "label": "S1"}, {"value": "s2", "label": "S2"}],
        },
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Shipped", "key": "shipped", "type": "boolean"},
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Stack",
            "key": "stack",
            "type": "multi_select",
            "options": [{"value": "fe", "label": "FE"}, {"value": "be", "label": "BE"}],
        },
    )

    existing = await _create_issue(test_client, user, "Old")

    headers = [
        "issue_code",
        "title",
        "status",
        "priority",
        "assignee_email",
        "reporter_email",
        "labels",
        "cycle",
        "estimate",
        "due_date",
        "created_at",
        "updated_at",
        "cf.severity",
        "cf.shipped",
        "cf.stack",
        "cf.unknown",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    writer.writerow(
        {
            "issue_code": existing["issue_code"],
            "title": "Updated CF",
            "status": "open",
            "priority": "high",
            "cf.severity": "s2",
            "cf.shipped": "true",
            "cf.stack": "fe",
            "cf.unknown": "ghost",
        }
    )
    writer.writerow(
        {
            "title": "Brand CF",
            "status": "open",
            "priority": "low",
            "cf.severity": "s1",
            "cf.shipped": "false",
            "cf.stack": "fe,be",
        }
    )
    writer.writerow(
        {
            "title": "Bad Bool",
            "status": "open",
            "priority": "medium",
            "cf.severity": "s1",
            "cf.shipped": "yes",
        }
    )
    csv_body = buf.getvalue()

    resp = await test_client.post(
        "/api/issues/import",
        headers=h,
        files={"file": ("issues.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["updated"] == 1, data
    assert data["created"] >= 2, data
    assert any("cf.unknown" in e["message"] for e in data["errors"]), data
    assert any("shipped" in e["message"] or "boolean" in e["message"] for e in data["errors"]), data

    got = await test_client.get(f"/api/issues/{existing['id']}", headers=h)
    assert got.status_code == 200
    body = got.json()["data"]
    assert body["title"] == "Updated CF"
    items = body.get("customFields") or body.get("custom_fields") or []
    cfs = {c.get("key"): c.get("value") for c in items}
    assert cfs.get("severity") == "s2", (cfs, data)
    assert cfs.get("shipped") is True, (cfs, data)
    assert cfs.get("stack") == ["fe"], (cfs, data)
