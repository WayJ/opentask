"""E91 CLI: issue board-move + version 1.75.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_75_0():
    assert __version__ == "1.75.0"
    assert VERSION == "1.75.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.75.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.75.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.75.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.75.0" in result.output


def test_api_client_move_issue_on_board_uses_post_snake_case():
    assert hasattr(OpenTaskClient, "move_issue_on_board")
    src = inspect.getsource(OpenTaskClient.move_issue_on_board)
    assert "/api/issues/board/move" in src
    assert "self.post" in src
    assert "issue_id" in src
    assert "ordered_ids" in src
    # must not send camelCase JSON keys as primary body keys
    assert '"issueId"' not in src
    assert "'issueId'" not in src
    assert '"orderedIds"' not in src
    assert "'orderedIds'" not in src
    # board-move must be POST, not PUT
    assert "self.put" not in src


def test_issue_help_lists_board_move():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "--help"])
    assert result.exit_code == 0
    assert "board-move" in result.output
    # neighbors still present
    assert "bulk-update" in result.output
    assert "update" in result.output
    assert "show" in result.output


def test_board_move_help_lists_flags():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "board-move", "--help"])
    assert result.exit_code == 0
    assert "--status" in result.output
    assert "--position" in result.output
    assert "--ordered-ids" in result.output


def test_issue_update_help_has_no_position_flag():
    """Q4a: do NOT add --position to issue update (board-move is the channel)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "update", "--help"])
    assert result.exit_code == 0
    # update help must not advertise a board --position flag
    assert "--position" not in result.output


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


def test_board_move_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_move(self, issue_id, status, position, ordered_ids=None):
        called["id"] = issue_id
        called["status"] = status
        called["position"] = position
        called["ordered_ids"] = ordered_ids
        return {"id": issue_id, "status": status, "position": position}

    monkeypatch.setattr(OpenTaskClient, "move_issue_on_board", fake_move)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "issue",
            "board-move",
            "deadbeef-0000-0000-0000-000000000001",
            "--status",
            "in_progress",
            "--position",
            "3",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "deadbeef-0000-0000-0000-000000000001"
    assert called.get("status") == "in_progress"
    assert called.get("position") == 3
    assert called.get("ordered_ids") is None
    assert "in_progress" in result.output


def test_board_move_with_ordered_ids(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_move(self, issue_id, status, position, ordered_ids=None):
        called["id"] = issue_id
        called["status"] = status
        called["position"] = position
        called["ordered_ids"] = list(ordered_ids) if ordered_ids is not None else None
        return {"id": issue_id, "status": status, "position": position}

    monkeypatch.setattr(OpenTaskClient, "move_issue_on_board", fake_move)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "issue",
            "board-move",
            "deadbeef-0000-0000-0000-000000000001",
            "--status",
            "open",
            "--position",
            "0",
            "--ordered-ids",
            "id-a,id-b,id-c",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("ordered_ids") == ["id-a", "id-b", "id-c"]
    assert called.get("status") == "open"
    assert called.get("position") == 0


def test_board_move_requires_status_and_position(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    runner = CliRunner()
    no_status = runner.invoke(cli, ["issue", "board-move", "deadbeef-0000-0000-0000-000000000001", "--position", "1"])
    assert no_status.exit_code != 0
    no_pos = runner.invoke(cli, ["issue", "board-move", "deadbeef-0000-0000-0000-000000000001", "--status", "open"])
    assert no_pos.exit_code != 0


def test_board_move_rejects_negative_position(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_move(self, *a, **k):
        raise AssertionError("should not call api for negative position")

    monkeypatch.setattr(OpenTaskClient, "move_issue_on_board", fake_move)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["issue", "board-move", "deadbeef-0000-0000-0000-000000000001", "--status", "open", "--position", "-1"],
    )
    assert result.exit_code != 0


def test_issue_show_human_includes_position(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, issue_id, by_code=False):
        return {
            "id": "deadbeef-0000-0000-0000-000000000001",
            "issue_code": "OT-1",
            "title": "Board item",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "position": 7,
            "estimate_points": None,
        }

    async def fake_comments(self, issue_id):
        return []

    async def fake_watchers(self, issue_id):
        return []

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get)
    monkeypatch.setattr(OpenTaskClient, "get_comments", fake_comments)
    monkeypatch.setattr(OpenTaskClient, "list_issue_watchers", fake_watchers)

    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "show", "deadbeef-0000-0000-0000-000000000001"])
    assert result.exit_code == 0, result.output
    assert "Position" in result.output
    assert "7" in result.output
