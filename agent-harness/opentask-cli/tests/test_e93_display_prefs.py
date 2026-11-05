"""E93 CLI: display-prefs get|set + version 1.80.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_77_0():
    assert __version__ == "1.80.0"
    assert VERSION == "1.80.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.80.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.80.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.80.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.80.0" in result.output


def test_api_client_get_issue_display_prefs():
    assert hasattr(OpenTaskClient, "get_issue_display_prefs")
    src = inspect.getsource(OpenTaskClient.get_issue_display_prefs)
    assert "/api/display-prefs/issue" in src
    assert "self.get" in src


def test_api_client_put_issue_display_prefs_snake_case_body():
    assert hasattr(OpenTaskClient, "put_issue_display_prefs")
    src = inspect.getsource(OpenTaskClient.put_issue_display_prefs)
    assert "/api/display-prefs/issue" in src
    assert "self.put" in src
    assert '"display"' in src or "'display'" in src
    # must not rewrite display keys to camelCase viewMode as the request contract
    assert "viewMode" not in src


def test_display_prefs_help_lists_get_set():
    runner = CliRunner()
    result = runner.invoke(cli, ["display-prefs", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output


def test_root_help_lists_display_prefs():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "display-prefs" in result.output


def test_view_write_and_board_move_still_in_help():
    runner = CliRunner()
    view = runner.invoke(cli, ["view", "--help"])
    assert view.exit_code == 0
    for name in ("create", "update", "delete", "favorite", "save-as", "list", "show", "use"):
        assert name in view.output
    issue = runner.invoke(cli, ["issue", "--help"])
    assert issue.exit_code == 0
    assert "board-move" in issue.output


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


def test_display_prefs_get_null(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {"n": 0}

    async def fake_get(self):
        called["n"] += 1
        return {"display": None}

    monkeypatch.setattr(OpenTaskClient, "get_issue_display_prefs", fake_get)
    runner = CliRunner()
    result = runner.invoke(cli, ["display-prefs", "get"])
    assert result.exit_code == 0, result.output
    assert called["n"] == 1
    out = result.output.lower()
    assert "null" in out or "无" in result.output or "none" in out or "absent" in out


def test_display_prefs_get_with_prefs_human(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self):
        return {
            "display": {
                "view_mode": "board",
                "group_by": "status",
                "swimlane_by": "assignee",
                "hide_empty_lanes": True,
            }
        }

    monkeypatch.setattr(OpenTaskClient, "get_issue_display_prefs", fake_get)
    runner = CliRunner()
    result = runner.invoke(cli, ["display-prefs", "get"])
    assert result.exit_code == 0, result.output
    assert "board" in result.output
    assert "status" in result.output or "View mode" in result.output or "view_mode" in result.output.lower()


def test_display_prefs_get_json(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self):
        return {"display": {"view_mode": "list"}}

    monkeypatch.setattr(OpenTaskClient, "get_issue_display_prefs", fake_get)
    runner = CliRunner()
    result = runner.invoke(cli, ["display-prefs", "get", "--json"])
    assert result.exit_code == 0, result.output
    assert "view_mode" in result.output
    assert "list" in result.output


def test_display_prefs_set_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_put(self, display):
        called["display"] = display
        return {"display": display}

    monkeypatch.setattr(OpenTaskClient, "put_issue_display_prefs", fake_put)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "display-prefs",
            "set",
            "--display",
            '{"view_mode":"board","group_by":"none"}',
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("display") == {"view_mode": "board", "group_by": "none"}
    assert "view_mode" in result.output


def test_display_prefs_set_rejects_invalid_json(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_put(self, display):
        raise AssertionError("should not call api for bad JSON")

    monkeypatch.setattr(OpenTaskClient, "put_issue_display_prefs", fake_put)
    runner = CliRunner()
    result = runner.invoke(cli, ["display-prefs", "set", "--display", "{not-json"])
    assert result.exit_code != 0


def test_display_prefs_set_rejects_non_object(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_put(self, display):
        raise AssertionError("should not call api for non-object")

    monkeypatch.setattr(OpenTaskClient, "put_issue_display_prefs", fake_put)
    runner = CliRunner()
    result = runner.invoke(cli, ["display-prefs", "set", "--display", '["a"]'])
    assert result.exit_code != 0


def test_display_prefs_set_human_summary(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_put(self, display):
        return {"display": display}

    monkeypatch.setattr(OpenTaskClient, "put_issue_display_prefs", fake_put)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "display-prefs",
            "set",
            "--display",
            '{"view_mode":"list","group_by":"priority","swimlane_by":"none"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert "list" in result.output
