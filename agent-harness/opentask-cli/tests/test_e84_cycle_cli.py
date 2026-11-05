"""E84 CLI: cycle generate-upcoming|update|delete + version 1.74.0."""
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


def test_version_pins_1_68_0():
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


def test_api_client_cycle_mid_methods_exist():
    assert hasattr(OpenTaskClient, "generate_upcoming_cycle")
    assert hasattr(OpenTaskClient, "update_cycle")
    assert hasattr(OpenTaskClient, "delete_cycle")


def test_cycle_help_lists_mid_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["cycle", "--help"])
    assert result.exit_code == 0
    assert "generate-upcoming" in result.output
    assert "update" in result.output
    assert "delete" in result.output


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


def test_cycle_generate_upcoming_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {"n": 0}

    async def fake_gen(self):
        called["n"] += 1
        return {"id": "cyc-next", "name": "Cycle 2", "status": "upcoming"}

    monkeypatch.setattr(OpenTaskClient, "generate_upcoming_cycle", fake_gen)

    runner = CliRunner()
    result = runner.invoke(cli, ["cycle", "generate-upcoming", "--json"])
    assert result.exit_code == 0, result.output
    assert called["n"] == 1
    assert "cyc-next" in result.output or "Cycle 2" in result.output


def test_cycle_update_sends_partial_fields(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, cycle_id, **kwargs):
        called["id"] = cycle_id
        called["kwargs"] = kwargs
        return {"id": cycle_id, "name": kwargs.get("name", "x")}

    monkeypatch.setattr(OpenTaskClient, "update_cycle", fake_update)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cycle", "update", "cyc-1", "--name", "Renamed", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "cyc-1"
    assert called.get("kwargs") == {"name": "Renamed"}
    assert "starts_at" not in called["kwargs"]
    assert "ends_at" not in called["kwargs"]


def test_cycle_update_requires_at_least_one_field(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_update(self, cycle_id, **kwargs):
        raise AssertionError("should not call api when no fields")

    monkeypatch.setattr(OpenTaskClient, "update_cycle", fake_update)

    runner = CliRunner()
    result = runner.invoke(cli, ["cycle", "update", "cyc-2", "--json"])
    assert result.exit_code != 0


def test_cycle_delete_calls_api_without_yes(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_delete(self, cycle_id):
        called["id"] = cycle_id
        return {"id": cycle_id}

    monkeypatch.setattr(OpenTaskClient, "delete_cycle", fake_delete)

    runner = CliRunner()
    # Q3a: no --yes required
    result = runner.invoke(cli, ["cycle", "delete", "cyc-del-1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "cyc-del-1"
    assert "cyc-del-1" in result.output or "deleted" in result.output.lower() or '"ok"' in result.output.lower() or "success" in result.output.lower()


def test_cycle_delete_help_has_no_yes_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["cycle", "delete", "--help"])
    assert result.exit_code == 0
    # Options section must not advertise a confirmation flag
    options = result.output.split("Options:", 1)[-1]
    assert "--yes" not in options
