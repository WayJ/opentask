"""E83 CLI: project watch|unwatch|watchers + show watching_count + version 1.69.0."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_67_0():
    assert __version__ == "1.69.0"
    assert VERSION == "1.69.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.69.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.69.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.69.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.69.0" in result.output


def test_api_client_project_watch_methods_exist():
    assert hasattr(OpenTaskClient, "watch_project")
    assert hasattr(OpenTaskClient, "unwatch_project")
    assert hasattr(OpenTaskClient, "list_project_watchers")


def test_project_help_lists_watch_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "--help"])
    assert result.exit_code == 0
    assert "watch" in result.output
    assert "unwatch" in result.output
    assert "watchers" in result.output


def _cfg(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "tok"
    cfg.active_workspace_id = "ws-1"
    return cfg


def test_project_watch_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_watch(self, project_id):
        called["id"] = project_id
        return {"id": "w1", "project_id": project_id, "user_id": "u1", "username": "alice"}

    monkeypatch.setattr(OpenTaskClient, "watch_project", fake_watch)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "watch", "proj-uuid-1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "proj-uuid-1"
    assert "watching" in result.output or "w1" in result.output or "alice" in result.output


def test_project_unwatch_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_unwatch(self, project_id):
        called["id"] = project_id
        return {}

    monkeypatch.setattr(OpenTaskClient, "unwatch_project", fake_unwatch)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "unwatch", "proj-uuid-2", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "proj-uuid-2"


def test_project_watchers_lists(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self, project_id):
        return [
            {
                "user_id": "u1",
                "username": "bob",
                "name": "Bob",
                "created_at": "2026-11-05T00:00:00",
            }
        ]

    monkeypatch.setattr(OpenTaskClient, "list_project_watchers", fake_list)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "watchers", "proj-uuid-3", "--json"])
    assert result.exit_code == 0, result.output
    assert "u1" in result.output or "bob" in result.output


def test_project_show_includes_watching_count(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, project_id):
        return {"id": project_id, "name": "Alpha", "is_active": True}

    async def fake_list(self, project_id):
        return [{"user_id": "u1"}, {"user_id": "u2"}]

    monkeypatch.setattr(OpenTaskClient, "get_project", fake_get)
    monkeypatch.setattr(OpenTaskClient, "list_project_watchers", fake_list)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "show", "proj-show-1", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    # tolerate either raw project dump or wrapped {success,data}
    payload = data.get("data") if isinstance(data, dict) and "data" in data and "watching_count" not in data else data
    if isinstance(payload, dict) and "data" in payload and "watching_count" in payload.get("data", {}):
        payload = payload["data"]
    assert payload.get("watching_count") == 2
    assert isinstance(payload.get("watchers"), list)
    assert len(payload["watchers"]) == 2


def test_project_show_watching_count_degrades(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, project_id):
        return {"id": project_id, "name": "Beta"}

    async def fake_list(self, project_id):
        from opentask.utils.api_client import APIError

        raise APIError("boom", status_code=500)

    monkeypatch.setattr(OpenTaskClient, "get_project", fake_get)
    monkeypatch.setattr(OpenTaskClient, "list_project_watchers", fake_list)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "show", "proj-show-2", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    payload = data.get("data") if isinstance(data, dict) and "watching_count" not in data and isinstance(data.get("data"), dict) else data
    assert payload.get("watching_count") == 0
    assert payload.get("watchers") == []
