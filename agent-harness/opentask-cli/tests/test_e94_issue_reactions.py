"""E94 CLI: issue reaction + comment-reaction list|add|remove + version 1.78.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_78_0():
    assert __version__ == "1.78.0"
    assert VERSION == "1.78.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.78.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.78.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.78.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.78.0" in result.output


def test_api_client_list_issue_reactions():
    assert hasattr(OpenTaskClient, "list_issue_reactions")
    src = inspect.getsource(OpenTaskClient.list_issue_reactions)
    assert "/api/issues/" in src
    assert "/reactions" in src
    assert "self.get" in src


def test_api_client_add_issue_reaction_emoji_body():
    assert hasattr(OpenTaskClient, "add_issue_reaction")
    src = inspect.getsource(OpenTaskClient.add_issue_reaction)
    assert "/reactions" in src
    assert "self.post" in src
    assert '"emoji"' in src or "'emoji'" in src


def test_api_client_remove_issue_reaction_query():
    assert hasattr(OpenTaskClient, "remove_issue_reaction")
    src = inspect.getsource(OpenTaskClient.remove_issue_reaction)
    assert "/reactions" in src
    assert "self.delete" in src
    assert "emoji" in src
    assert "params" in src


def test_api_client_list_comment_reactions():
    assert hasattr(OpenTaskClient, "list_comment_reactions")
    src = inspect.getsource(OpenTaskClient.list_comment_reactions)
    assert "/comments/" in src
    assert "/reactions" in src
    assert "self.get" in src


def test_api_client_add_comment_reaction_emoji_body():
    assert hasattr(OpenTaskClient, "add_comment_reaction")
    src = inspect.getsource(OpenTaskClient.add_comment_reaction)
    assert "/comments/" in src
    assert "/reactions" in src
    assert "self.post" in src
    assert '"emoji"' in src or "'emoji'" in src


def test_api_client_remove_comment_reaction_query():
    assert hasattr(OpenTaskClient, "remove_comment_reaction")
    src = inspect.getsource(OpenTaskClient.remove_comment_reaction)
    assert "/comments/" in src
    assert "/reactions" in src
    assert "self.delete" in src
    assert "emoji" in src
    assert "params" in src


def test_issue_help_lists_reaction_groups():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "--help"])
    assert result.exit_code == 0
    assert "reaction" in result.output
    assert "comment-reaction" in result.output
    # neighbors still present
    assert "comment" in result.output
    assert "board-move" in result.output
    assert "bulk-update" in result.output


def test_issue_reaction_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "reaction", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "remove" in result.output


def test_issue_comment_reaction_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "comment-reaction", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "remove" in result.output


def test_comment_group_still_intact():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "comment", "--help"])
    assert result.exit_code == 0
    assert "add" in result.output
    assert "list" in result.output
    assert "attachment" in result.output


def test_display_prefs_and_view_write_still_in_help():
    runner = CliRunner()
    dp = runner.invoke(cli, ["display-prefs", "--help"])
    assert dp.exit_code == 0
    assert "get" in dp.output
    assert "set" in dp.output
    view = runner.invoke(cli, ["view", "--help"])
    assert view.exit_code == 0
    for name in ("create", "update", "delete", "favorite", "save-as", "list", "show", "use"):
        assert name in view.output


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


ISSUE = "deadbeef-0000-0000-0000-000000000001"
COMMENT = "cafebabe-0000-0000-0000-000000000002"


def test_issue_reaction_list_empty(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {"n": 0}

    async def fake_list(self, issue_id):
        called["n"] += 1
        called["id"] = issue_id
        return {"rows": [], "total": 0}

    monkeypatch.setattr(OpenTaskClient, "list_issue_reactions", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "reaction", "list", ISSUE])
    assert result.exit_code == 0, result.output
    assert called["n"] == 1
    assert called["id"] == ISSUE
    out = result.output.lower()
    assert "无" in result.output or "empty" in out or "0" in result.output or "none" in out


def test_issue_reaction_list_human_table(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self, issue_id):
        return {
            "rows": [{"emoji": "👍", "count": 2, "users": ["u1", "u2"]}],
            "total": 1,
        }

    monkeypatch.setattr(OpenTaskClient, "list_issue_reactions", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "reaction", "list", ISSUE])
    assert result.exit_code == 0, result.output
    assert "👍" in result.output
    assert "2" in result.output


def test_issue_reaction_list_json(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self, issue_id):
        return {"rows": [{"emoji": "🎉", "count": 1}], "total": 1}

    monkeypatch.setattr(OpenTaskClient, "list_issue_reactions", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "reaction", "list", ISSUE, "--json"])
    assert result.exit_code == 0, result.output
    assert "🎉" in result.output
    assert "rows" in result.output or "total" in result.output


def test_issue_reaction_add_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_add(self, issue_id, emoji):
        called["id"] = issue_id
        called["emoji"] = emoji
        return {"reaction_id": "rx-1"}

    monkeypatch.setattr(OpenTaskClient, "add_issue_reaction", fake_add)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["issue", "reaction", "add", ISSUE, "--emoji", "👍", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == ISSUE
    assert called.get("emoji") == "👍"
    assert "rx-1" in result.output or "reaction" in result.output.lower()


def test_issue_reaction_add_missing_emoji_no_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_add(self, issue_id, emoji):
        raise AssertionError("should not call api without --emoji")

    monkeypatch.setattr(OpenTaskClient, "add_issue_reaction", fake_add)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "reaction", "add", ISSUE])
    assert result.exit_code != 0


def test_issue_reaction_remove_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_rm(self, issue_id, emoji):
        called["id"] = issue_id
        called["emoji"] = emoji
        return None

    monkeypatch.setattr(OpenTaskClient, "remove_issue_reaction", fake_rm)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["issue", "reaction", "remove", ISSUE, "--emoji", "👍"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == ISSUE
    assert called.get("emoji") == "👍"


def test_issue_reaction_remove_missing_emoji_no_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_rm(self, issue_id, emoji):
        raise AssertionError("should not call api without --emoji")

    monkeypatch.setattr(OpenTaskClient, "remove_issue_reaction", fake_rm)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "reaction", "remove", ISSUE])
    assert result.exit_code != 0


def test_comment_reaction_list_human(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_list(self, issue_id, comment_id):
        called["issue"] = issue_id
        called["comment"] = comment_id
        return {"reactions": {"👍": ["u1", "u2"], "🎉": ["u3"]}}

    monkeypatch.setattr(OpenTaskClient, "list_comment_reactions", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "comment-reaction", "list", ISSUE, COMMENT])
    assert result.exit_code == 0, result.output
    assert called.get("issue") == ISSUE
    assert called.get("comment") == COMMENT
    assert "👍" in result.output
    assert "🎉" in result.output


def test_comment_reaction_add_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_add(self, issue_id, comment_id, emoji):
        called["issue"] = issue_id
        called["comment"] = comment_id
        called["emoji"] = emoji
        return {"reaction_id": "crx-1", "reactions": {emoji: ["me"]}}

    monkeypatch.setattr(OpenTaskClient, "add_comment_reaction", fake_add)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "issue",
            "comment-reaction",
            "add",
            ISSUE,
            COMMENT,
            "--emoji",
            "🔥",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("issue") == ISSUE
    assert called.get("comment") == COMMENT
    assert called.get("emoji") == "🔥"


def test_comment_reaction_remove_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_rm(self, issue_id, comment_id, emoji):
        called["issue"] = issue_id
        called["comment"] = comment_id
        called["emoji"] = emoji
        return {"reactions": {}}

    monkeypatch.setattr(OpenTaskClient, "remove_comment_reaction", fake_rm)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "issue",
            "comment-reaction",
            "remove",
            ISSUE,
            COMMENT,
            "--emoji",
            "🔥",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("issue") == ISSUE
    assert called.get("comment") == COMMENT
    assert called.get("emoji") == "🔥"


def test_comment_reaction_add_missing_emoji_no_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_add(self, issue_id, comment_id, emoji):
        raise AssertionError("should not call api without --emoji")

    monkeypatch.setattr(OpenTaskClient, "add_comment_reaction", fake_add)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["issue", "comment-reaction", "add", ISSUE, COMMENT]
    )
    assert result.exit_code != 0
