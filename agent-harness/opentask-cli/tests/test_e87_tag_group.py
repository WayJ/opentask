"""E87 CLI: label group list|create|update|delete + list/create --group-id + update str + version 1.71.0."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_71_0():
    assert __version__ == "1.71.0"
    assert VERSION == "1.71.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.71.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.71.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.71.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.71.0" in result.output


def test_api_client_tag_group_methods_exist():
    assert hasattr(OpenTaskClient, "list_tag_groups")
    assert hasattr(OpenTaskClient, "create_tag_group")
    assert hasattr(OpenTaskClient, "update_tag_group")
    assert hasattr(OpenTaskClient, "delete_tag_group")
    assert hasattr(OpenTaskClient, "list_tags")
    assert hasattr(OpenTaskClient, "create_tag")
    assert hasattr(OpenTaskClient, "update_tag")


def test_label_help_lists_group():
    runner = CliRunner()
    result = runner.invoke(cli, ["label", "--help"])
    assert result.exit_code == 0
    assert "group" in result.output
    assert "list" in result.output
    assert "create" in result.output
    assert "set" in result.output
    assert "update" in result.output


def test_label_group_help_lists_crud():
    runner = CliRunner()
    result = runner.invoke(cli, ["label", "group", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
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


def test_label_group_list_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_list(self):
        called["ok"] = True
        return {"rows": [{"id": "g1", "name": "Priority"}], "total": 1}

    monkeypatch.setattr(OpenTaskClient, "list_tag_groups", fake_list)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "group", "list", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("ok") is True
    assert "Priority" in result.output


def test_label_group_create_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_create(self, name, color=None, position=0):
        called["name"] = name
        called["color"] = color
        called["position"] = position
        return {"id": "g-new", "name": name, "color": color, "position": position}

    monkeypatch.setattr(OpenTaskClient, "create_tag_group", fake_create)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["label", "group", "create", "--name", "Severity", "--color", "#ff0000", "--position", "2", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("name") == "Severity"
    assert called.get("color") == "#ff0000"
    assert called.get("position") == 2
    assert "Severity" in result.output


def test_label_group_update_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, group_id, *, name=None, color=None, position=None):
        called["id"] = group_id
        called["name"] = name
        called["color"] = color
        called["position"] = position
        return {"id": group_id, "name": name or "G", "color": color, "position": position}

    monkeypatch.setattr(OpenTaskClient, "update_tag_group", fake_update)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["label", "group", "update", "g-uuid-1", "--name", "Renamed", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "g-uuid-1"
    assert called.get("name") == "Renamed"


def test_label_group_update_requires_field(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["label", "group", "update", "g-uuid-1"])
    assert result.exit_code != 0


def test_label_group_delete_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_delete(self, group_id):
        called["id"] = group_id
        return {"id": group_id}

    monkeypatch.setattr(OpenTaskClient, "delete_tag_group", fake_delete)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "group", "delete", "g-del", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "g-del"


def test_label_list_group_id_filter(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_list_tags(self, group_id=None, q=None):
        called["group_id"] = group_id
        called["q"] = q
        return {"rows": [{"id": 1, "name": "bug", "group_id": group_id}], "total": 1}

    monkeypatch.setattr(OpenTaskClient, "list_tags", fake_list_tags)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["label", "list", "--group-id", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("group_id") == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_label_create_with_group_id(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_create_tag(self, name, color=None, group_id=None):
        called["name"] = name
        called["color"] = color
        called["group_id"] = group_id
        return {"id": 9, "name": name, "color": color, "group_id": group_id}

    monkeypatch.setattr(OpenTaskClient, "create_tag", fake_create_tag)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["label", "create", "--name", "P0", "--group-id", "gggggggg-1111-2222-3333-444444444444", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("name") == "P0"
    assert called.get("group_id") == "gggggggg-1111-2222-3333-444444444444"
    assert isinstance(called.get("group_id"), str)


def test_label_update_group_id_is_str_uuid(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, tag_id, *, name=None, color=None, group_id=None, clear_group=False):
        called["id"] = str(tag_id)
        called["group_id"] = group_id
        called["clear_group"] = clear_group
        return {"id": int(tag_id) if str(tag_id).isdigit() else tag_id, "group_id": group_id}

    monkeypatch.setattr(OpenTaskClient, "update_tag", fake_update)

    gid = "ffffffff-aaaa-bbbb-cccc-dddddddddddd"
    runner = CliRunner()
    result = runner.invoke(cli, ["label", "update", "42", "--group-id", gid, "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("group_id") == gid
    assert isinstance(called.get("group_id"), str)
    assert not isinstance(called.get("group_id"), int)


def test_label_update_clear_group_still_works(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, tag_id, *, name=None, color=None, group_id=None, clear_group=False):
        called["clear_group"] = clear_group
        called["group_id"] = group_id
        return {"id": 7, "group_id": None}

    monkeypatch.setattr(OpenTaskClient, "update_tag", fake_update)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "update", "7", "--clear-group", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("clear_group") is True
