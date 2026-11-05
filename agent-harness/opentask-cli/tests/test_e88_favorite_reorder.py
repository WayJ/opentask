"""E88 CLI: favorite reorder + list position + version 1.79.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_72_0():
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


def test_api_client_reorder_favorites_exists_and_uses_put():
    assert hasattr(OpenTaskClient, "reorder_favorites")
    src = inspect.getsource(OpenTaskClient.reorder_favorites)
    assert "/api/favorites/reorder" in src
    assert "self.put" in src
    assert "self.post" not in src
    assert "ordered_ids" in src


def test_favorite_help_lists_reorder():
    runner = CliRunner()
    result = runner.invoke(cli, ["favorite", "--help"])
    assert result.exit_code == 0
    assert "reorder" in result.output
    assert "list" in result.output
    assert "add" in result.output
    assert "remove" in result.output


def test_favorite_reorder_help_lists_ids():
    runner = CliRunner()
    result = runner.invoke(cli, ["favorite", "reorder", "--help"])
    assert result.exit_code == 0
    assert "--ids" in result.output


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


def test_favorite_reorder_ids_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_reorder(self, ordered_ids):
        called["ids"] = list(ordered_ids)
        return {"rows": [{"id": i, "position": n} for n, i in enumerate(ordered_ids)], "total": len(ordered_ids)}

    monkeypatch.setattr(OpenTaskClient, "reorder_favorites", fake_reorder)

    runner = CliRunner()
    result = runner.invoke(cli, ["favorite", "reorder", "--ids", "a,b,c", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("ids") == ["a", "b", "c"]
    assert "a" in result.output


def test_favorite_reorder_positional_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_reorder(self, ordered_ids):
        called["ids"] = list(ordered_ids)
        return {"rows": [], "total": 0}

    monkeypatch.setattr(OpenTaskClient, "reorder_favorites", fake_reorder)

    runner = CliRunner()
    result = runner.invoke(cli, ["favorite", "reorder", "id1", "id2", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("ids") == ["id1", "id2"]


def test_favorite_reorder_requires_ids(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["favorite", "reorder"])
    assert result.exit_code != 0


def test_favorite_list_shows_position(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self):
        return {
            "rows": [
                {
                    "id": "fav-1",
                    "target_type": "project",
                    "target_id": "p-1",
                    "position": 0,
                },
                {
                    "id": "fav-2",
                    "targetType": "issue",
                    "targetId": "i-1",
                    "position": 1,
                },
            ],
            "total": 2,
        }

    monkeypatch.setattr(OpenTaskClient, "list_favorites", fake_list)

    runner = CliRunner()
    result = runner.invoke(cli, ["favorite", "list", "--json"])
    assert result.exit_code == 0, result.output
    assert "position" in result.output
    assert '"position": 0' in result.output or '"position":0' in result.output

    result_h = runner.invoke(cli, ["favorite", "list"])
    assert result_h.exit_code == 0, result_h.output
    assert "Position" in result_h.output or "position" in result_h.output.lower()
    # short id + position digit should appear
    assert "0" in result_h.output
