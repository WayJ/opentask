"""E89 CLI: custom-field reorder + version 1.74.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_73_0():
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


def test_api_client_reorder_custom_fields_exists_and_uses_post_ordered_ids():
    assert hasattr(OpenTaskClient, "reorder_custom_fields")
    src = inspect.getsource(OpenTaskClient.reorder_custom_fields)
    assert "/api/custom-fields/reorder" in src
    assert "self.post" in src
    assert "self.put" not in src
    assert "orderedIds" in src
    # must not send snake_case JSON key for this endpoint
    assert '"ordered_ids"' not in src
    assert "'ordered_ids'" not in src


def test_custom_field_help_lists_reorder():
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "--help"])
    assert result.exit_code == 0
    assert "reorder" in result.output
    assert "list" in result.output
    assert "create" in result.output
    assert "update" in result.output
    assert "validate-formula" in result.output


def test_custom_field_reorder_help_lists_ids():
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "reorder", "--help"])
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


def test_custom_field_reorder_ids_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_reorder(self, ordered_ids):
        called["ids"] = list(ordered_ids)
        return {
            "rows": [{"id": i, "position": n} for n, i in enumerate(ordered_ids)],
            "total": len(ordered_ids),
        }

    monkeypatch.setattr(OpenTaskClient, "reorder_custom_fields", fake_reorder)

    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "reorder", "--ids", "a,b,c", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("ids") == ["a", "b", "c"]
    assert "a" in result.output


def test_custom_field_reorder_positional_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_reorder(self, ordered_ids):
        called["ids"] = list(ordered_ids)
        return {"rows": [], "total": 0}

    monkeypatch.setattr(OpenTaskClient, "reorder_custom_fields", fake_reorder)

    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "reorder", "id1", "id2", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("ids") == ["id1", "id2"]


def test_custom_field_reorder_requires_ids(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "reorder"])
    assert result.exit_code != 0
