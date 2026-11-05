"""E23：Workspace 实时通道 — hub 广播、WS 鉴权、跨租户负例。"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any
from urllib.parse import urlencode

import pytest
from httpx import AsyncClient

from opentask.services.workspace_realtime import events
from opentask.services.workspace_realtime.hub import (
    WorkspaceRealtimeHub,
    reset_workspace_realtime_hub_for_tests,
)


class _FakeWS:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_json(self, data):
        self.sent.append(data)


class _ASGIWebSocketSession:
    """最小 ASGI WebSocket 客户端（兼容 httpx 0.28 + starlette 0.27）。"""

    def __init__(self, app, path: str, query: dict[str, str] | None = None):
        self.app = app
        self.path = path
        self.query_string = urlencode(query or {}).encode()
        self._send_q: asyncio.Queue = asyncio.Queue()
        self._recv_q: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.accepted = False
        self.close_code: int | None = None

    async def __aenter__(self):
        self._task = asyncio.create_task(self._run())
        # 等待 accept 或 close
        msg = await asyncio.wait_for(self._recv_q.get(), timeout=5)
        if msg["type"] == "websocket.close":
            self.close_code = msg.get("code", 1000)
            raise _WSClosed(self.close_code)
        if msg["type"] != "websocket.accept":
            raise AssertionError(f"expected accept, got {msg}")
        self.accepted = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._send_q.put({"type": "websocket.disconnect", "code": 1000})
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=2)
            except Exception:  # noqa: BLE001
                self._task.cancel()

    async def _run(self):
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": self.path,
            "raw_path": self.path.encode(),
            "query_string": self.query_string,
            "root_path": "",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "subprotocols": [],
            "state": {},
            "extensions": {"websocket.http.response": True},
        }

        async def receive():
            return await self._send_q.get()

        async def send(message):
            await self._recv_q.put(message)

        await self._send_q.put({"type": "websocket.connect"})
        await self.app(scope, receive, send)

    async def receive_json(self, timeout: float = 5.0) -> dict[str, Any]:
        while True:
            msg = await asyncio.wait_for(self._recv_q.get(), timeout=timeout)
            if msg["type"] == "websocket.close":
                self.close_code = msg.get("code", 1000)
                raise _WSClosed(self.close_code)
            if msg["type"] == "websocket.send":
                if "text" in msg:
                    return json.loads(msg["text"])
                if "bytes" in msg:
                    return json.loads(msg["bytes"].decode())
            # ignore other

    async def send_json(self, data: dict):
        await self._send_q.put(
            {"type": "websocket.receive", "text": json.dumps(data)}
        )


class _WSClosed(Exception):
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"WebSocket closed: {code}")


@pytest.fixture(autouse=True)
def _reset_hub():
    reset_workspace_realtime_hub_for_tests()
    yield
    reset_workspace_realtime_hub_for_tests()


@pytest.mark.asyncio
async def test_hub_broadcast_skips_actor():
    hub = WorkspaceRealtimeHub()
    a = _FakeWS()
    b = _FakeWS()
    await hub.connect(a, user_id="actor", workspace_id="ws1")
    await hub.connect(b, user_id="peer", workspace_id="ws1")

    n = await hub.publish(
        "ws1",
        events.ISSUE_CREATED,
        {"id": "i1", "issue_code": "KEY-1"},
        actor_user_id="actor",
        skip_actor=True,
    )
    assert n == 1
    assert not a.sent
    assert b.sent[0]["type"] == events.ISSUE_CREATED
    assert b.sent[0]["payload"]["issue_code"] == "KEY-1"


@pytest.mark.asyncio
async def test_hub_no_cross_workspace_leak():
    hub = WorkspaceRealtimeHub()
    a = _FakeWS()
    b = _FakeWS()
    await hub.connect(a, user_id="u1", workspace_id="ws-a")
    await hub.connect(b, user_id="u2", workspace_id="ws-b")

    await hub.publish(
        "ws-a",
        events.ISSUE_UPDATED,
        {"id": "i1", "changed": ["status"]},
        actor_user_id="other",
    )
    assert len(a.sent) == 1
    assert not b.sent


async def _register(client: AsyncClient, prefix: str = "rt"):
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
    }


@pytest.mark.asyncio
async def test_ws_workspace_route_registered():
    from opentask.api.websocket import router as websocket_router

    paths = [route.path for route in websocket_router.routes if hasattr(route, "path")]
    assert "/ws/workspace" in paths


@pytest.mark.asyncio
async def test_ws_rejects_bad_token(app, test_client: AsyncClient):
    user = await _register(test_client, "rt_bad")
    async with _ASGIWebSocketSession(
        app,
        "/ws/workspace",
        {"token": "not-a-token", "workspace_id": user["workspaceId"]},
    ) as ws:
        with pytest.raises(_WSClosed) as exc:
            await ws.receive_json()
    assert exc.value.code in (4401, 4403, 1008)


@pytest.mark.asyncio
async def test_ws_rejects_non_member(app, test_client: AsyncClient):
    owner = await _register(test_client, "rt_own")
    stranger = await _register(test_client, "rt_str")
    async with _ASGIWebSocketSession(
        app,
        "/ws/workspace",
        {"token": stranger["token"], "workspace_id": owner["workspaceId"]},
    ) as ws:
        with pytest.raises(_WSClosed) as exc:
            await ws.receive_json()
    assert exc.value.code == 4403


@pytest.mark.asyncio
async def test_ws_member_receives_connected_and_issue_event(app, test_client: AsyncClient):
    owner = await _register(test_client, "rt_ok")
    peer = await _register(test_client, "rt_peer")
    resp = await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={"userId": peer["userId"], "role": "member"},
    )
    assert resp.status_code == 200, resp.text

    async with _ASGIWebSocketSession(
        app,
        "/ws/workspace",
        {"token": peer["token"], "workspace_id": owner["workspaceId"]},
    ) as ws:
        hello = await ws.receive_json()
        assert hello["type"] == "connected"
        assert hello["workspace_id"] == owner["workspaceId"]

        created = await test_client.post(
            "/api/issues",
            headers={
                "Authorization": f"Bearer {owner['token']}",
                "X-Workspace-Id": owner["workspaceId"],
            },
            json={
                "title": "realtime ping",
                "type": "feature",
                "status": "open",
                "priority": "medium",
            },
        )
        assert created.status_code == 200, created.text
        evt = await ws.receive_json()
        assert evt["type"] == events.ISSUE_CREATED
        assert evt["workspace_id"] == owner["workspaceId"]
        assert evt["payload"]["id"] == created.json()["data"]["id"]
        assert evt["payload"].get("issue_code")

        await ws.send_json({"type": "ping"})
        pong = await ws.receive_json()
        assert pong["type"] == "pong"


@pytest.mark.asyncio
async def test_ws_event_does_not_cross_tenant(app, test_client: AsyncClient):
    a = await _register(test_client, "rt_a")
    b = await _register(test_client, "rt_b")
    async with _ASGIWebSocketSession(
        app,
        "/ws/workspace",
        {"token": b["token"], "workspace_id": b["workspaceId"]},
    ) as ws_b:
        assert (await ws_b.receive_json())["type"] == "connected"
        created = await test_client.post(
            "/api/issues",
            headers={
                "Authorization": f"Bearer {a['token']}",
                "X-Workspace-Id": a["workspaceId"],
            },
            json={
                "title": "should not leak",
                "type": "feature",
                "status": "open",
                "priority": "medium",
            },
        )
        assert created.status_code == 200, created.text
        await ws_b.send_json({"type": "ping"})
        msg = await ws_b.receive_json()
        assert msg["type"] == "pong"
