"""E96 CLI: access-token list|create|revoke(+rm) + version 1.80.0.

Security: tests use ONLY the obvious fake token below. Never call real
create endpoints or touch the user's real ~/.opentask config.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]

# Obvious fake — never a real credential
FAKE_TOKEN = "vk_TEST_ONLY_NOT_A_REAL_TOKEN"
TOKEN_ID = "deadbeef-0000-0000-0000-0000000000aa"


def test_version_pins_1_80_0():
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


def test_api_client_list_access_tokens():
    assert hasattr(OpenTaskClient, "list_access_tokens")
    src = inspect.getsource(OpenTaskClient.list_access_tokens)
    assert "/api/access-tokens" in src
    assert "self.get" in src


def test_api_client_create_access_token_body():
    assert hasattr(OpenTaskClient, "create_access_token")
    src = inspect.getsource(OpenTaskClient.create_access_token)
    assert "/api/access-tokens" in src
    assert "self.post" in src
    assert '"name"' in src or "'name'" in src
    # optional description supported
    assert "description" in src


def test_api_client_delete_access_token():
    assert hasattr(OpenTaskClient, "delete_access_token")
    src = inspect.getsource(OpenTaskClient.delete_access_token)
    assert "/api/access-tokens/" in src
    assert "self.delete" in src


def test_api_client_no_get_by_id_or_update_helpers():
    assert not hasattr(OpenTaskClient, "get_access_token")
    assert not hasattr(OpenTaskClient, "update_access_token")
    assert not hasattr(OpenTaskClient, "rename_access_token")


def test_top_level_help_lists_access_token_group():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "access-token" in result.output


def test_config_set_access_token_still_present():
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "set-access-token" in result.output


def test_access_token_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "--help"])
    assert result.exit_code == 0
    for name in ("list", "create", "revoke"):
        assert name in result.output


def test_neighbor_helps_untouched():
    runner = CliRunner()
    repo = runner.invoke(cli, ["project", "repo", "--help"])
    assert repo.exit_code == 0
    assert "list" in repo.output
    rx = runner.invoke(cli, ["issue", "reaction", "--help"])
    assert rx.exit_code == 0
    assert "list" in rx.output
    dp = runner.invoke(cli, ["display-prefs", "--help"])
    assert dp.exit_code == 0
    assert "get" in dp.output
    assert "set" in dp.output


def _cfg(tmp_path, monkeypatch, *, access_token=None):
    """Isolate config under tmp_path — never touch real ~/.opentask."""
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "jwt-test-not-real"
    cfg.active_workspace_id = "ws-1"
    if access_token is not None:
        cfg.access_token = access_token
    return cfg


def test_access_token_list_empty(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {"n": 0}

    async def fake_list(self):
        called["n"] += 1
        return []

    monkeypatch.setattr(OpenTaskClient, "list_access_tokens", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "list"])
    assert result.exit_code == 0, result.output
    assert called["n"] == 1
    out = result.output.lower()
    assert (
        "无" in result.output
        or "empty" in out
        or "0" in result.output
        or "none" in out
        or "no " in out
    )


def test_access_token_list_human_table_no_raw_token(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self):
        return [
            {
                "id": TOKEN_ID,
                "name": "ci-bot",
                "token_prefix": "vk_TEST",
                "expires_at": "2027-11-05T00:00:00Z",
                "last_used_at": None,
            }
        ]

    monkeypatch.setattr(OpenTaskClient, "list_access_tokens", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "list"])
    assert result.exit_code == 0, result.output
    assert "ci-bot" in result.output
    assert "vk_TEST" in result.output
    assert TOKEN_ID in result.output or TOKEN_ID[:8] in result.output
    # list must never print a full token value (response has none)
    assert FAKE_TOKEN not in result.output


def test_access_token_list_json(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self):
        return [
            {
                "id": "1",
                "name": "n",
                "token_prefix": "vk_xxxx",
                "expires_at": "2027-01-01T00:00:00Z",
                "last_used_at": None,
            }
        ]

    monkeypatch.setattr(OpenTaskClient, "list_access_tokens", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "list", "--json"])
    assert result.exit_code == 0, result.output
    assert "vk_xxxx" in result.output
    assert "rows" in result.output or "n" in result.output


def test_access_token_create_calls_api_and_prints_once(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_create(self, name, description=None):
        called["name"] = name
        called["description"] = description
        return {
            "id": TOKEN_ID,
            "name": name,
            "description": description,
            "token_prefix": "vk_TEST",
            "token": FAKE_TOKEN,
            "expires_at": "2027-11-05T00:00:00Z",
            "last_used_at": None,
        }

    monkeypatch.setattr(OpenTaskClient, "create_access_token", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "access-token",
            "create",
            "--name",
            "agent-key",
            "--description",
            "for tests only",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("name") == "agent-key"
    assert called.get("description") == "for tests only"
    assert FAKE_TOKEN in result.output
    # one-time visibility hint (Chinese or English)
    low = result.output.lower()
    assert (
        "仅此一次" in result.output
        or "once" in low
        or "only once" in low
        or "one-time" in low
        or "one time" in low
    )


def test_access_token_create_default_does_not_write_config(tmp_path, monkeypatch):
    sentinel = "vk_SENTINEL_PREVIOUS_NOT_REAL"
    _cfg(tmp_path, monkeypatch, access_token=sentinel)

    async def fake_create(self, name, description=None):
        return {
            "id": TOKEN_ID,
            "name": name,
            "token_prefix": "vk_TEST",
            "token": FAKE_TOKEN,
        }

    monkeypatch.setattr(OpenTaskClient, "create_access_token", fake_create)
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "create", "--name", "no-save"])
    assert result.exit_code == 0, result.output
    # re-load isolated config — must still be sentinel, not FAKE_TOKEN
    cfg = Config()
    assert cfg.access_token == sentinel
    assert cfg.access_token != FAKE_TOKEN


def test_access_token_create_save_writes_isolated_config(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch, access_token=None)

    async def fake_create(self, name, description=None):
        return {
            "id": TOKEN_ID,
            "name": name,
            "token_prefix": "vk_TEST",
            "token": FAKE_TOKEN,
        }

    monkeypatch.setattr(OpenTaskClient, "create_access_token", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["access-token", "create", "--name", "with-save", "--save"]
    )
    assert result.exit_code == 0, result.output
    cfg = Config()
    assert cfg.access_token == FAKE_TOKEN


def test_access_token_create_json_includes_token(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_create(self, name, description=None):
        return {
            "id": TOKEN_ID,
            "name": name,
            "token_prefix": "vk_TEST",
            "token": FAKE_TOKEN,
        }

    monkeypatch.setattr(OpenTaskClient, "create_access_token", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["access-token", "create", "--name", "j", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    data = payload.get("data") or payload
    assert isinstance(data, dict)
    assert data.get("token") == FAKE_TOKEN or (
        isinstance(data.get("data"), dict) and data["data"].get("token") == FAKE_TOKEN
    ) or FAKE_TOKEN in result.output


def test_access_token_create_missing_name_no_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_create(self, *a, **k):
        raise AssertionError("should not call api without --name")

    monkeypatch.setattr(OpenTaskClient, "create_access_token", fake_create)
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "create"])
    assert result.exit_code != 0


def test_access_token_revoke_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_rm(self, token_id):
        called["id"] = str(token_id)
        return True

    monkeypatch.setattr(OpenTaskClient, "delete_access_token", fake_rm)
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "revoke", TOKEN_ID])
    assert result.exit_code == 0, result.output
    assert called.get("id") == TOKEN_ID


def test_access_token_rm_alias(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {"n": 0}

    async def fake_rm(self, token_id):
        called["n"] += 1
        return True

    monkeypatch.setattr(OpenTaskClient, "delete_access_token", fake_rm)
    runner = CliRunner()
    result = runner.invoke(cli, ["access-token", "rm", TOKEN_ID])
    assert result.exit_code == 0, result.output
    assert called["n"] == 1
