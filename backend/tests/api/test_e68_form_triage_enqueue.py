"""E68: public form → triage enqueue mid."""
from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

os.environ["OPENTASK_FORM_RATE_LIMIT"] = "0"

DEFAULT_FIELDS = [
    {"key": "title", "type": "title", "label": "标题", "required": True},
    {"key": "description", "type": "description", "label": "描述"},
]


async def _register(client: AsyncClient, prefix: str = "e68"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
        "username": uname,
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


@pytest.mark.asyncio
async def test_e68_form_enqueue_triage_default_false_and_patch(test_client: AsyncClient):
    user = await _register(test_client, "e68_crud")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "TriageForm", "fields": DEFAULT_FIELDS},
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row.get("enqueueTriage") is False
    fid = row["id"]

    patched = await test_client.patch(
        f"/api/forms/{fid}",
        headers=h,
        json={"enqueueTriage": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["enqueueTriage"] is True

    got = await test_client.get(f"/api/forms/{fid}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["enqueueTriage"] is True

    created_on = await test_client.post(
        "/api/forms",
        headers=h,
        json={
            "name": "TriageOn",
            "fields": DEFAULT_FIELDS,
            "enqueueTriage": True,
        },
    )
    assert created_on.status_code == 200, created_on.text
    assert created_on.json()["data"]["enqueueTriage"] is True


@pytest.mark.asyncio
async def test_e68_submit_default_not_enqueued(test_client: AsyncClient):
    user = await _register(test_client, "e68_off")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "Off", "fields": DEFAULT_FIELDS},
    )
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "plain"}},
    )
    assert submitted.status_code == 200, submitted.text
    data = submitted.json()["data"]
    assert data.get("triageEnqueued") is False
    issue = await test_client.get(f"/api/issues/{data['issueId']}", headers=h)
    assert issue.status_code == 200, issue.text
    body = issue.json()["data"]
    assert (body.get("triageStatus") or body.get("triage_status")) in (None, "", "null")
    triage = await test_client.get("/api/triage", headers=h)
    assert triage.status_code == 200, triage.text
    ids = [r["id"] for r in triage.json()["data"]["rows"]]
    assert data["issueId"] not in ids


@pytest.mark.asyncio
async def test_e68_submit_enqueue_pending_and_list(test_client: AsyncClient):
    user = await _register(test_client, "e68_on")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "On", "fields": DEFAULT_FIELDS, "enqueueTriage": True},
    )
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "needs triage"}},
    )
    assert submitted.status_code == 200, submitted.text
    data = submitted.json()["data"]
    assert data.get("triageEnqueued") is True
    issue = await test_client.get(f"/api/issues/{data['issueId']}", headers=h)
    body = issue.json()["data"]
    assert (body.get("triageStatus") or body.get("triage_status")) == "pending"
    triage = await test_client.get("/api/triage", headers=h)
    ids = [r["id"] for r in triage.json()["data"]["rows"]]
    assert data["issueId"] in ids
    # accept clears
    acc = await test_client.post(f"/api/triage/{data['issueId']}/accept", headers=h)
    assert acc.status_code == 200, acc.text
    assert acc.json()["data"].get("triageStatus") in (None, "")


@pytest.mark.asyncio
async def test_e68_enqueue_with_customer_request(test_client: AsyncClient):
    user = await _register(test_client, "e68_cr")
    h = _auth(user["token"], user["workspaceId"])
    cust = await test_client.post(
        "/api/customers", headers=h, json={"name": f"C-{uuid.uuid4().hex[:6]}"}
    )
    assert cust.status_code == 200, cust.text
    cid = cust.json()["data"]["id"]
    fields = list(DEFAULT_FIELDS) + [
        {"key": "customer_id", "type": "customer_id", "label": "客户", "required": True}
    ]
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={
            "name": "Both",
            "fields": fields,
            "enqueueTriage": True,
            "createCustomerRequest": True,
        },
    )
    assert created.status_code == 200, created.text
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "both paths", "customer_id": cid}},
    )
    assert submitted.status_code == 200, submitted.text
    data = submitted.json()["data"]
    assert data.get("triageEnqueued") is True
    assert data.get("requestId")
    issue = await test_client.get(f"/api/issues/{data['issueId']}", headers=h)
    body = issue.json()["data"]
    assert (body.get("triageStatus") or body.get("triage_status")) == "pending"


@pytest.mark.asyncio
async def test_e68_enqueue_idempotent_already_pending(test_client: AsyncClient):
    """Re-enqueue via Triage API must stay pending (idempotent)."""
    user = await _register(test_client, "e68_idemp")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "Idemp", "fields": DEFAULT_FIELDS, "enqueueTriage": True},
    )
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "once"}},
    )
    iid = submitted.json()["data"]["issueId"]
    again = await test_client.post(
        "/api/triage",
        headers=h,
        json={"issueId": iid},
    )
    assert again.status_code == 200, again.text
    assert again.json()["data"].get("triageStatus") == "pending"



@pytest.mark.asyncio
async def test_e68_enqueue_no_new_webhook_fire(test_client: AsyncClient):
    user = await _register(test_client, "e68_spy")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "Spy", "fields": DEFAULT_FIELDS, "enqueueTriage": True},
    )
    token = created.json()["data"]["token"]
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        submitted = await test_client.post(
            f"/api/public/forms/{token}/submit",
            json={"values": {"title": "spy"}},
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["data"]["triageEnqueued"] is True
        triage_events = []
        for c in fw.call_args_list:
            blob = " ".join(str(a) for a in c.args) + " " + " ".join(
                f"{k}={v}" for k, v in c.kwargs.items()
            )
            if "triage" in blob.lower():
                triage_events.append(blob)
        assert triage_events == []
