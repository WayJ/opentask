import json
import pytest
from opentask.services.oauth2.token_service import OAuthTokenService
from opentask.models.issue.model import Issue
import uuid


@pytest.mark.asyncio
async def test_mcp_uses_member_oauth_scope_and_issue_surface(test_client, test_session, oauth_user, registered_client):
    issue = Issue(
        issue_code="ISSUE2026-" + str(100000 + uuid.uuid4().int % 800000),
        title="MCP issue",
        type="bug",
        status="open",
        priority="medium",
        reporter_id=str(oauth_user.id),
        created_by=str(oauth_user.id),
    )
    test_session.add(issue)
    await test_session.commit()
    client, _ = registered_client
    token = await OAuthTokenService(test_session).issue(user=oauth_user, client_id=client.client_id, scope="read:tasks")
    headers = {"Authorization": "Bearer " + token["access_token"]}

    async def call(method, params=None):
        return await test_client.post(
            "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        )

    init = await call("initialize")
    assert init.status_code == 200 and init.json()["result"]["protocolVersion"] == "2025-03-26"
    notified = await test_client.post(
        "/mcp", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    assert notified.status_code == 202 and not notified.content
    listing = await call("tools/list")
    assert "list_issues" in [tool["name"] for tool in listing.json()["result"]["tools"]]
    result = await call("tools/call", {"name": "list_issues", "arguments": {"limit": 10, "offset": 0}})
    assert result.status_code == 200
    data = json.loads(result.json()["result"]["content"][0]["text"])
    reference = await test_client.get("/oauth2/api/tasks?limit=10&offset=0", headers=headers)
    assert data == reference.json()
    assert any(item["id"] == issue.id and item["title"] == "MCP issue" for item in data["items"])
    invalid = await call("tools/call", {"name": "list_issues", "arguments": {"limit": True}})
    assert invalid.status_code == 400
    unexpected = await call("tools/call", {"name": "list_issues", "arguments": {"extra": 1}})
    assert unexpected.status_code == 400
    no_token = await test_client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert no_token.status_code == 401
    no_scope = await OAuthTokenService(test_session).issue(user=oauth_user, client_id=client.client_id, scope="profile")
    forbidden = await test_client.post(
        "/mcp",
        headers={"Authorization": "Bearer " + no_scope["access_token"]},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert forbidden.status_code == 200
    assert "list_issues" not in [tool["name"] for tool in forbidden.json()["result"]["tools"]]
    forbidden_call = await test_client.post(
        "/mcp",
        headers={"Authorization": "Bearer " + no_scope["access_token"]},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_issues"}},
    )
    assert forbidden_call.status_code == 403
