"""E14: workspace commands + KEY-N / header smoke."""
from __future__ import annotations

from unittest import mock

import pytest
from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config


@pytest.fixture
def runner_config(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    return cfg_dir


def test_workspace_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["workspace", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "use" in result.output


def test_workspace_use_persists(runner_config, monkeypatch):
    runner = CliRunner()

    async def fake_list(self):
        return [{"id": "ws-full-uuid-001", "name": "Alpha", "slug": "alpha", "role": "owner", "issueKey": "AL"}]

    async def fake_get(self, wid):
        return {"id": wid, "name": "Alpha"}

    monkeypatch.setattr(OpenTaskClient, "list_workspaces", fake_list)
    monkeypatch.setattr(OpenTaskClient, "get_workspace", fake_get)

    result = runner.invoke(cli, ["workspace", "use", "ws-full"])
    assert result.exit_code == 0, result.output
    cfg = Config()
    assert cfg.active_workspace_id == "ws-full-uuid-001"
    assert cfg.active_workspace_name == "Alpha"

    result2 = runner.invoke(cli, ["workspace", "current", "--json"])
    assert result2.exit_code == 0
    assert "ws-full-uuid-001" in result2.output


def test_new_command_helps():
    runner = CliRunner()
    for cmd in ["cycle", "label", "triage", "inbox", "favorite", "view", "member", "invite", "initiative", "doc"]:
        result = runner.invoke(cli, [cmd, "--help"])
        assert result.exit_code == 0, cmd
        assert result.output


@pytest.mark.asyncio
async def test_api_client_workspace_and_cycle_paths():
    client = OpenTaskClient(base_url="http://example.test", token="t")
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value=[])) as g:
        await client.list_workspaces()
        g.assert_awaited_with("/api/workspaces")
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_cycles()
        g.assert_awaited()
        assert g.await_args.args[0] == "/api/cycles"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_tags()
        assert g.await_args.args[0] == "/api/tags"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_triage()
        assert g.await_args.args[0] == "/api/triage"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_inbox()
        assert g.await_args.args[0] == "/api/inbox"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_favorites()
        assert g.await_args.args[0] == "/api/favorites"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_saved_views()
        assert g.await_args.args[0] == "/api/saved-views"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_initiatives()
        assert g.await_args.args[0] == "/api/initiatives"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_entity_docs("issue", "i1")
        assert g.await_args.args[0] == "/api/entity-documents"
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"rows": []})) as g:
        await client.list_issue_children("i1")
        assert g.await_args.args[0] == "/api/issues/i1/children"


@pytest.mark.asyncio
async def test_headers_sent_on_request(tmp_path):
    cfg = Config()
    cfg.config_dir = tmp_path / ".opentask"
    cfg.config_file = cfg.config_dir / "config.json"
    cfg._data = {}
    cfg.active_workspace_id = "ws-9"
    cfg.token = "tok"
    client = OpenTaskClient(base_url="http://example.test", token="tok", config=cfg)

    captured = {}

    class FakeResp:
        status_code = 200
        def json(self):
            return {"code": 200, "data": {"ok": True}}

    class FakeClient:
        def __init__(self, *a, **k):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def request(self, method, url, headers=None, **kwargs):
            captured["headers"] = headers
            captured["url"] = url
            return FakeResp()

    with mock.patch("httpx.AsyncClient", FakeClient):
        data = await client.get("/api/cycles")
    assert captured["headers"]["X-Workspace-Id"] == "ws-9"
    assert data == {"ok": True}


def test_issue_children_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "children", "--help"])
    assert result.exit_code == 0
    result = runner.invoke(cli, ["issue", "relation", "--help"])
    assert result.exit_code == 0


def test_version_1_6_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.21.0" in result.output
