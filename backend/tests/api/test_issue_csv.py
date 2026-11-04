"""E28：Issue CSV export / import."""
from __future__ import annotations

import csv
import io
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "csv"):
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
        "password": password,
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _add_member(client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


async def _create_issue(client: AsyncClient, user: dict, title: str = "csv-issue", **extra) -> dict:
    payload = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        "reporter_id": user["userId"],
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_export_columns_and_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "csv_ex")
    issue = await _create_issue(test_client, user, title="Export Me", priority="high")

    missing = await test_client.get(
        "/api/issues/export.csv",
        headers={"Authorization": f"Bearer {user['token']}"},
    )
    assert missing.status_code == 400

    resp = await test_client.get(
        "/api/issues/export.csv",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers.get("content-type", "")
    text = resp.text
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames is not None
    for col in (
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
    ):
        assert col in reader.fieldnames
    rows = list(reader)
    assert any(r["title"] == "Export Me" and r["issue_code"] == issue["issue_code"] for r in rows)
    assert any(r["priority"] == "high" for r in rows if r["title"] == "Export Me")


@pytest.mark.asyncio
async def test_import_create_update_and_row_errors(test_client: AsyncClient):
    owner = await _register(test_client, "csv_im")
    outsider = await _register(test_client, "csv_out")

    # seed one issue to update
    existing = await _create_issue(test_client, owner, title="Old Title")

    csv_body = (
        "issue_code,title,status,priority,assignee_email,reporter_email,labels,cycle,estimate,due_date,created_at,updated_at\n"
        f"{existing['issue_code']},Updated Title,in_progress,high,{owner['username']},,bug;csv,,3,2026-12-01,,\n"
        ",Brand New,open,low,,,,,2,,,\n"
        ",Missing Assignee,open,medium,not_a_member@x,,,,,,,\n"
        ",,open,medium,,,,,,,,\n"  # empty title
    )

    # viewer cannot import
    viewer = await _register(test_client, "csv_v")
    await _add_member(test_client, owner, viewer, role="viewer")
    forbid = await test_client.post(
        "/api/issues/import",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        files={"file": ("issues.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert forbid.status_code == 403, forbid.text

    resp = await test_client.post(
        "/api/issues/import",
        headers=_auth(owner["token"], owner["workspaceId"]),
        files={"file": ("issues.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["updated"] == 1, data
    assert data["created"] == 1, data
    assert len(data["errors"]) >= 2, data
    assert any("title" in e["message"] for e in data["errors"])
    assert any("assignee" in e["message"] for e in data["errors"])

    # verify update
    got = await test_client.get(
        f"/api/issues/{existing['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert got.status_code == 200
    body = got.json()["data"]
    assert body["title"] == "Updated Title"
    assert body["status"] == "in_progress"
    assert body["priority"] == "high"
    assert body.get("estimate_points") == 3 or body.get("estimatePoints") == 3

    # outsider WS cannot see export of owner's issues
    other_export = await test_client.get(
        "/api/issues/export.csv",
        headers=_auth(outsider["token"], outsider["workspaceId"]),
    )
    assert other_export.status_code == 200
    assert existing["issue_code"] not in other_export.text


@pytest.mark.asyncio
async def test_import_bad_file_and_template(test_client: AsyncClient):
    user = await _register(test_client, "csv_bad")
    bad = await test_client.post(
        "/api/issues/import",
        headers=_auth(user["token"], user["workspaceId"]),
        files={"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")},
    )
    assert bad.status_code == 400

    tmpl = await test_client.get(
        "/api/issues/import/template.csv",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert tmpl.status_code == 200
    assert "title" in tmpl.text
    assert "issue_code" in tmpl.text
