"""E85 CLI: project health get|set + timeline + show health + version 1.70.0."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_69_0():
    assert __version__ == "1.70.0"
    assert VERSION == "1.70.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.70.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.70.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.70.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.70.0" in result.output


def test_api_client_project_health_methods_exist():
    assert hasattr(OpenTaskClient, "get_project_health")
    assert hasattr(OpenTaskClient, "post_project_health")
    assert hasattr(OpenTaskClient, "get_project_timeline")


def test_project_help_lists_health_and_timeline():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "--help"])
    assert result.exit_code == 0
    assert "health" in result.output
    assert "timeline" in result.output


def test_project_health_help_lists_get_set():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "health", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output


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


def test_project_health_get_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_get(self, project_id, *, history=False):
        called["id"] = project_id
        called["history"] = history
        return {
            "latest": {"status": "on_track", "note": "ok", "project_id": project_id},
            "history": [],
        }

    monkeypatch.setattr(OpenTaskClient, "get_project_health", fake_get)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "health", "get", "proj-h1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "proj-h1"
    assert called.get("history") is False
    assert "on_track" in result.output


def test_project_health_get_with_history(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_get(self, project_id, *, history=False):
        called["history"] = history
        return {
            "latest": {"status": "at_risk", "note": "slip"},
            "history": [
                {"status": "at_risk", "note": "slip"},
                {"status": "on_track", "note": "ok"},
            ],
        }

    monkeypatch.setattr(OpenTaskClient, "get_project_health", fake_get)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["project", "health", "get", "proj-h2", "--history", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("history") is True
    assert "at_risk" in result.output


def test_project_health_set_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_post(self, project_id, *, status, note=None):
        called["id"] = project_id
        called["status"] = status
        called["note"] = note
        return {"id": "hu1", "status": status, "note": note, "project_id": project_id}

    monkeypatch.setattr(OpenTaskClient, "post_project_health", fake_post)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "project",
            "health",
            "set",
            "proj-h3",
            "--status",
            "off_track",
            "--note",
            "blocked",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "proj-h3"
    assert called.get("status") == "off_track"
    assert called.get("note") == "blocked"
    assert "off_track" in result.output


def test_project_health_set_requires_status(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_post(self, project_id, *, status, note=None):
        raise AssertionError("should not call api without status")

    monkeypatch.setattr(OpenTaskClient, "post_project_health", fake_post)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "health", "set", "proj-h4", "--json"])
    assert result.exit_code != 0


def test_project_timeline_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_tl(self, project_id):
        called["id"] = project_id
        return {
            "project": {"id": project_id, "name": "Alpha", "health_status": "on_track"},
            "milestones": [],
            "issues": [],
        }

    monkeypatch.setattr(OpenTaskClient, "get_project_timeline", fake_tl)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "timeline", "proj-tl1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "proj-tl1"
    assert "Alpha" in result.output or "on_track" in result.output or "proj-tl1" in result.output


def test_project_show_includes_health(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, project_id):
        return {"id": project_id, "name": "Alpha", "is_active": True}

    async def fake_watchers(self, project_id):
        return []

    async def fake_health(self, project_id, *, history=False):
        return {
            "latest": {"status": "at_risk", "note": "slip", "project_id": project_id},
            "history": [],
        }

    monkeypatch.setattr(OpenTaskClient, "get_project", fake_get)
    monkeypatch.setattr(OpenTaskClient, "list_project_watchers", fake_watchers)
    monkeypatch.setattr(OpenTaskClient, "get_project_health", fake_health)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "show", "proj-show-h1", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    payload = data
    if isinstance(data, dict) and "health" not in data and isinstance(data.get("data"), dict):
        payload = data["data"]
    assert payload.get("health_status") == "at_risk"
    health = payload.get("health")
    assert isinstance(health, dict)
    assert health.get("status") == "at_risk"


def test_project_show_health_degrades(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, project_id):
        return {"id": project_id, "name": "Beta"}

    async def fake_watchers(self, project_id):
        return []

    async def fake_health(self, project_id, *, history=False):
        from opentask.utils.api_client import APIError

        raise APIError("boom", status_code=500)

    monkeypatch.setattr(OpenTaskClient, "get_project", fake_get)
    monkeypatch.setattr(OpenTaskClient, "list_project_watchers", fake_watchers)
    monkeypatch.setattr(OpenTaskClient, "get_project_health", fake_health)

    runner = CliRunner()
    result = runner.invoke(cli, ["project", "show", "proj-show-h2", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    payload = data
    if isinstance(data, dict) and "name" not in data and isinstance(data.get("data"), dict):
        payload = data["data"]
    # degrade: null/None health, still shows project
    assert payload.get("name") == "Beta" or payload.get("id") == "proj-show-h2"
    assert payload.get("health") is None or payload.get("health") == {}
    assert payload.get("health_status") in (None, "")
