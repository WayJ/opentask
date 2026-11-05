"""E92 CLI: view create|update|delete|favorite|save-as + version 1.79.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_76_0():
    assert __version__ == "1.79.0"
    assert VERSION == "1.79.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.79.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.79.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.79.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.79.0" in result.output


def test_api_client_create_saved_view_post_snake_case():
    assert hasattr(OpenTaskClient, "create_saved_view")
    src = inspect.getsource(OpenTaskClient.create_saved_view)
    assert "/api/saved-views" in src
    assert "self.post" in src
    assert "is_favorite" in src
    assert "is_shared" in src
    assert '"isFavorite"' not in src
    assert "'isFavorite'" not in src
    assert '"isShared"' not in src
    assert "'isShared'" not in src


def test_api_client_update_saved_view_patch_snake_case():
    assert hasattr(OpenTaskClient, "update_saved_view")
    src = inspect.getsource(OpenTaskClient.update_saved_view)
    assert "/api/saved-views/" in src
    assert "self.patch" in src
    assert "is_favorite" in src
    assert "is_shared" in src
    assert '"isFavorite"' not in src
    assert "'isFavorite'" not in src


def test_api_client_delete_saved_view():
    assert hasattr(OpenTaskClient, "delete_saved_view")
    src = inspect.getsource(OpenTaskClient.delete_saved_view)
    assert "/api/saved-views/" in src
    assert "self.delete" in src


def test_api_client_set_saved_view_favorite():
    assert hasattr(OpenTaskClient, "set_saved_view_favorite")
    src = inspect.getsource(OpenTaskClient.set_saved_view_favorite)
    assert "/favorite" in src
    assert "self.post" in src
    assert "is_favorite" in src
    assert '"isFavorite"' not in src
    assert "'isFavorite'" not in src


def test_api_client_save_as_saved_view():
    assert hasattr(OpenTaskClient, "save_as_saved_view")
    src = inspect.getsource(OpenTaskClient.save_as_saved_view)
    assert "/save-as" in src
    assert "self.post" in src


def test_view_help_lists_write_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "--help"])
    assert result.exit_code == 0
    for name in ("create", "update", "delete", "favorite", "save-as", "list", "show", "use"):
        assert name in result.output


def test_issue_board_move_still_in_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "--help"])
    assert result.exit_code == 0
    assert "board-move" in result.output


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


def test_view_create_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_create(self, name, filter=None, sort=None, display=None, is_favorite=None, is_shared=None):
        called["name"] = name
        called["filter"] = filter
        called["sort"] = sort
        called["display"] = display
        called["is_favorite"] = is_favorite
        called["is_shared"] = is_shared
        return {"id": "v1", "name": name, "isFavorite": bool(is_favorite), "isShared": bool(is_shared)}

    monkeypatch.setattr(OpenTaskClient, "create_saved_view", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "view",
            "create",
            "--name",
            "My View",
            "--filter",
            '{"status":"open"}',
            "--favorite",
            "--shared",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("name") == "My View"
    assert called.get("filter") == {"status": "open"}
    assert called.get("is_favorite") is True
    assert called.get("is_shared") is True
    assert "My View" in result.output or "v1" in result.output


def test_view_create_rejects_invalid_filter_json(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_create(self, *a, **k):
        raise AssertionError("should not call api for bad JSON")

    monkeypatch.setattr(OpenTaskClient, "create_saved_view", fake_create)
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "create", "--name", "X", "--filter", "{not-json"])
    assert result.exit_code != 0


def test_view_update_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, view_id, **kwargs):
        called["id"] = view_id
        called.update(kwargs)
        return {"id": view_id, "name": kwargs.get("name") or "n"}

    monkeypatch.setattr(OpenTaskClient, "update_saved_view", fake_update)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "view",
            "update",
            "deadbeef-0000-0000-0000-000000000001",
            "--name",
            "Renamed",
            "--no-favorite",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "deadbeef-0000-0000-0000-000000000001"
    assert called.get("name") == "Renamed"
    assert called.get("is_favorite") is False


def test_view_delete_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_delete(self, view_id):
        called["id"] = view_id
        return {"id": view_id}

    monkeypatch.setattr(OpenTaskClient, "delete_saved_view", fake_delete)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["view", "delete", "deadbeef-0000-0000-0000-000000000001", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "deadbeef-0000-0000-0000-000000000001"


def test_view_favorite_on_off(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_fav(self, view_id, is_favorite):
        called["id"] = view_id
        called["is_favorite"] = is_favorite
        return {"id": view_id, "isFavorite": is_favorite}

    monkeypatch.setattr(OpenTaskClient, "set_saved_view_favorite", fake_fav)
    runner = CliRunner()
    on = runner.invoke(
        cli,
        ["view", "favorite", "deadbeef-0000-0000-0000-000000000001", "--on", "--json"],
    )
    assert on.exit_code == 0, on.output
    assert called.get("is_favorite") is True
    off = runner.invoke(
        cli,
        ["view", "favorite", "deadbeef-0000-0000-0000-000000000002", "--off", "--json"],
    )
    assert off.exit_code == 0, off.output
    assert called.get("id") == "deadbeef-0000-0000-0000-000000000002"
    assert called.get("is_favorite") is False


def test_view_favorite_requires_on_or_off(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_fav(self, *a, **k):
        raise AssertionError("should not call")

    monkeypatch.setattr(OpenTaskClient, "set_saved_view_favorite", fake_fav)
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "favorite", "deadbeef-0000-0000-0000-000000000001"])
    assert result.exit_code != 0


def test_view_save_as_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_save(self, view_id, name=None):
        called["id"] = view_id
        called["name"] = name
        return {"id": "copy-1", "name": name or "Copy", "isShared": False}

    monkeypatch.setattr(OpenTaskClient, "save_as_saved_view", fake_save)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "view",
            "save-as",
            "deadbeef-0000-0000-0000-000000000001",
            "--name",
            "My Copy",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "deadbeef-0000-0000-0000-000000000001"
    assert called.get("name") == "My Copy"


def test_view_list_human_includes_favorite(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self):
        return {
            "rows": [
                {
                    "id": "deadbeef-0000-0000-0000-000000000001",
                    "name": "Fav View",
                    "isFavorite": True,
                    "isShared": False,
                }
            ]
        }

    monkeypatch.setattr(OpenTaskClient, "list_saved_views", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "list"])
    assert result.exit_code == 0, result.output
    assert "Favorite" in result.output
    assert "Shared" in result.output
    assert "Fav View" in result.output


def test_view_show_human_includes_favorite_shared(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, view_id):
        return {
            "id": view_id,
            "name": "Show Me",
            "filter": {"status": "open"},
            "isFavorite": True,
            "isShared": False,
        }

    monkeypatch.setattr(OpenTaskClient, "get_saved_view", fake_get)
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "show", "deadbeef-0000-0000-0000-000000000001"])
    assert result.exit_code == 0, result.output
    assert "Favorite" in result.output
    assert "Shared" in result.output
    assert "Show Me" in result.output


def test_view_use_still_prints_filters(tmp_path, monkeypatch):
    """Q4a: do not change view use default behavior."""
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, view_id):
        return {"id": view_id, "name": "U", "filter": {"priority": "high"}}

    monkeypatch.setattr(OpenTaskClient, "get_saved_view", fake_get)
    runner = CliRunner()
    result = runner.invoke(cli, ["view", "use", "deadbeef-0000-0000-0000-000000000001"])
    assert result.exit_code == 0, result.output
    assert "priority" in result.output
    assert "high" in result.output
