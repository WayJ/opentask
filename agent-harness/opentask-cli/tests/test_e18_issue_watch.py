"""E18: issue watch/unwatch/watchers CLI wiring."""
from __future__ import annotations

from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config


def test_api_client_watch_methods_exist():
    assert hasattr(OpenTaskClient, "watch_issue")
    assert hasattr(OpenTaskClient, "unwatch_issue")
    assert hasattr(OpenTaskClient, "list_issue_watchers")


def test_issue_watch_calls_api(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "tok"
    cfg.active_workspace_id = "ws-1"

    called = {}

    async def fake_get(self, issue_id, by_code=False):
        return {"id": "uuid-1", "issue_code": "OT-1", "title": "t"}

    async def fake_watch(self, issue_id):
        called["id"] = issue_id
        return {"id": "w1", "issue_id": issue_id, "user_id": "u1"}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get)
    monkeypatch.setattr(OpenTaskClient, "watch_issue", fake_watch)

    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "watch", "OT-1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "uuid-1"
    assert "watching" in result.output or "w1" in result.output


def test_issue_unwatch_calls_api(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "tok"
    cfg.active_workspace_id = "ws-1"

    called = {}

    async def fake_get(self, issue_id, by_code=False):
        return {"id": "uuid-1", "issue_code": "OT-1", "title": "t"}

    async def fake_unwatch(self, issue_id):
        called["id"] = issue_id
        return {}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get)
    monkeypatch.setattr(OpenTaskClient, "unwatch_issue", fake_unwatch)

    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "unwatch", "OT-1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "uuid-1"


def test_issue_watchers_lists(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "tok"
    cfg.active_workspace_id = "ws-1"

    async def fake_get(self, issue_id, by_code=False):
        return {"id": "uuid-1", "issue_code": "OT-1", "title": "t"}

    async def fake_list(self, issue_id):
        return [{"user_id": "u1", "created_at": "2026-11-04T00:00:00"}]

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get)
    monkeypatch.setattr(OpenTaskClient, "list_issue_watchers", fake_list)

    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "watchers", "OT-1", "--json"])
    assert result.exit_code == 0, result.output
    assert "u1" in result.output
